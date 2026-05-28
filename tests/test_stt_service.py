"""Tests for stt_service.py — MlxWhisperTranscriber + factory."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from runtime.media.stt_service import (
    MlxWhisperTranscriber,
    SimulatedTranscriber,
    create_transcriber,
)
from runtime.media.transcription import DeepgramTranscriber


# ─── Factory ──────────────────────────────────────────────────────────────────

def test_create_transcriber_default_is_mlx_whisper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STT_BACKEND", raising=False)
    t = create_transcriber()
    assert isinstance(t, MlxWhisperTranscriber)


def test_create_transcriber_deepgram(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STT_BACKEND", "deepgram")
    t = create_transcriber()
    assert isinstance(t, DeepgramTranscriber)


def test_create_transcriber_simulated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STT_BACKEND", "simulated")
    t = create_transcriber()
    assert isinstance(t, SimulatedTranscriber)


def test_stats_include_model_resolution_fields() -> None:
    t = MlxWhisperTranscriber()
    stats = t.stats()
    for key in ("model_source", "resolved_model_target", "download_root", "local_files_only"):
        assert key in stats


# ─── INPUT_FORMAT ─────────────────────────────────────────────────────────────

def test_mlx_whisper_input_format() -> None:
    assert MlxWhisperTranscriber.INPUT_FORMAT == "pcm16_16k"


def test_deepgram_input_format() -> None:
    assert DeepgramTranscriber.INPUT_FORMAT == "mulaw_8k"


def test_simulated_input_format() -> None:
    assert SimulatedTranscriber.INPUT_FORMAT == "mulaw_8k"


# ─── MlxWhisperTranscriber — connect ───────────────────────────────────────

def _make_mock_model(segments=None):
    """Return a mock WhisperModel with .transcribe() returning segments."""
    mock_model = MagicMock()
    if segments is None:
        segments = []
    mock_info = MagicMock()
    mock_model.transcribe.return_value = (iter(segments), mock_info)
    return mock_model


def _make_segment(text: str, avg_logprob: float = -0.1) -> MagicMock:
    seg = MagicMock()
    seg.text = text
    seg.avg_logprob = avg_logprob
    return seg


async def _connect_with_mock_model(transcriber, model):
    """Patch MLX model so connect() returns without downloading anything."""
    with patch("runtime.media.stt_service.MlxWhisperTranscriber._load_model_sync", return_value=model):
        return await transcriber.connect()


def test_connect_loads_model_in_executor() -> None:
    t = MlxWhisperTranscriber()
    mock_model = _make_mock_model()

    async def go():
        result = await _connect_with_mock_model(t, mock_model)
        await t.close()
        return result

    assert asyncio.run(go()) is True
    assert t._model is None  # model cleared by close()


def test_connect_returns_false_on_model_load_error() -> None:
    t = MlxWhisperTranscriber()

    with patch(
        "runtime.media.stt_service.MlxWhisperTranscriber._load_model_sync",
        side_effect=RuntimeError("model not found"),
    ):
        result = asyncio.run(t.connect())

    assert result is False


def test_model_path_override_forces_local_files_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHISPER_MODEL_PATH", "/tmp/fw-small-en")
    t = MlxWhisperTranscriber()
    target, kwargs = t._resolve_model_target()
    assert target == "/tmp/fw-small-en"
    assert kwargs["local_files_only"] is True


def test_download_root_and_local_files_only_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WHISPER_MODEL_PATH", raising=False)
    monkeypatch.setenv("WHISPER_DOWNLOAD_ROOT", "/tmp/hf-cache")
    monkeypatch.setenv("WHISPER_LOCAL_FILES_ONLY", "true")
    t = MlxWhisperTranscriber()
    target, kwargs = t._resolve_model_target()
    assert target == t._model_size
    assert kwargs["download_root"] == "/tmp/hf-cache"
    assert kwargs["local_files_only"] is True


# ─── MlxWhisperTranscriber — process_audio ─────────────────────────────────

def test_process_audio_queues_utterance() -> None:
    t = MlxWhisperTranscriber()
    mock_model = _make_mock_model()

    async def go():
        await _connect_with_mock_model(t, mock_model)
        await t.process_audio(bytes(640))
        assert t._utterances_queued == 1
        await t.close()

    asyncio.run(go())


def test_process_audio_before_connect_drops_silently() -> None:
    """process_audio before connect() should not raise."""
    t = MlxWhisperTranscriber()

    async def go():
        await t.process_audio(bytes(640))  # model is None — should be a no-op
        assert t._utterances_queued == 0

    asyncio.run(go())


# ─── MlxWhisperTranscriber — transcription callback ────────────────────────

def test_transcription_emits_on_transcript_callback() -> None:
    received = []
    t = MlxWhisperTranscriber(on_transcript=lambda text, final, sfinal: received.append(text))
    seg = _make_segment("press one for billing", avg_logprob=-0.1)
    mock_model = _make_mock_model([seg])

    async def go():
        await _connect_with_mock_model(t, mock_model)
        t._model = mock_model  # ensure model is set post-connect
        mock_model.transcribe.return_value = (iter([seg]), MagicMock())
        await t.process_audio(bytes(640))
        await t.close()

    asyncio.run(go())
    assert "press one for billing" in received


def test_low_confidence_transcript_dropped() -> None:
    received = []
    # Confidence min default is 0.6; avg_logprob=-3 → exp(-3)≈0.05
    t = MlxWhisperTranscriber(
        on_transcript=lambda text, f, sf: received.append(text),
        confidence_min=0.6,
    )
    seg = _make_segment("mumble", avg_logprob=-3.0)
    mock_model = _make_mock_model([seg])

    async def go():
        await _connect_with_mock_model(t, mock_model)
        t._model = mock_model
        mock_model.transcribe.return_value = (iter([seg]), MagicMock())
        await t.process_audio(bytes(640))
        await t.close()

    asyncio.run(go())
    assert received == []


def test_high_confidence_transcript_passes() -> None:
    received = []
    # avg_logprob=-0.1 → exp(-0.1)≈0.90 — well above 0.6
    t = MlxWhisperTranscriber(
        on_transcript=lambda text, f, sf: received.append(text),
        confidence_min=0.6,
    )
    seg = _make_segment("account number", avg_logprob=-0.1)
    mock_model = _make_mock_model([seg])

    async def go():
        await _connect_with_mock_model(t, mock_model)
        t._model = mock_model
        mock_model.transcribe.return_value = (iter([seg]), MagicMock())
        await t.process_audio(bytes(640))
        await t.close()

    asyncio.run(go())
    assert "account number" in received


# ─── MlxWhisperTranscriber — stats ─────────────────────────────────────────

def test_stats_contains_expected_keys() -> None:
    t = MlxWhisperTranscriber()
    s = t.stats()
    for key in (
        "backend",
        "model",
        "utterances_queued",
        "transcripts_emitted",
        "connected",
        "queue_size",
        "max_queue_size_seen",
        "utterances_dropped_queue_full",
        "last_connect_ms",
        "last_inference_ms",
    ):
        assert key in s, f"Missing key: {key}"


def test_stats_backend_is_mlx_whisper() -> None:
    assert MlxWhisperTranscriber().stats()["backend"] == "mlx-whisper"


# ─── _transcribe_sync (unit — no model download) ──────────────────────────────

def test_transcribe_sync_returns_text_confidence_pairs() -> None:
    t = MlxWhisperTranscriber()
    seg = _make_segment("hello world", avg_logprob=-0.2)
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([seg]), MagicMock())
    t._model = mock_model

    # 640 bytes of int16 zeros — valid PCM16 input
    result = t._transcribe_sync(bytes(640))
    assert isinstance(result, list)
    assert len(result) == 1
    text, conf = result[0]
    assert text == "hello world"
    assert 0.0 < conf <= 1.0


def test_transcribe_sync_filters_empty_segments() -> None:
    t = MlxWhisperTranscriber()
    seg_empty = _make_segment("", avg_logprob=-0.1)
    seg_blank = _make_segment("   ", avg_logprob=-0.1)
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter([seg_empty, seg_blank]), MagicMock())
    t._model = mock_model

    result = t._transcribe_sync(bytes(640))
    assert result == []