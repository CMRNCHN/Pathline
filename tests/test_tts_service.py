"""Tests for tts_service.py — PiperTTS + OpenAITTS + factory."""
from __future__ import annotations

import asyncio
import io
import struct
import wave
from unittest.mock import AsyncMock, patch

import pytest

from runtime.media.tts_service import (
    OpenAITTS,
    PiperNotFoundError,
    PiperTTS,
    _LRUCache,
    create_tts,
)


# ─── Factory ──────────────────────────────────────────────────────────────────

def test_create_tts_default_is_piper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TTS_BACKEND", raising=False)
    assert isinstance(create_tts(), PiperTTS)


def test_create_tts_piper_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TTS_BACKEND", "piper")
    assert isinstance(create_tts(), PiperTTS)


def test_create_tts_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TTS_BACKEND", "openai")
    assert isinstance(create_tts(), OpenAITTS)


# ─── LRU Cache ────────────────────────────────────────────────────────────────

def test_lru_cache_hit() -> None:
    c = _LRUCache(maxsize=3)
    c.set("a", b"data")
    assert c.get("a") == b"data"


def test_lru_cache_miss_returns_none() -> None:
    c = _LRUCache(maxsize=3)
    assert c.get("missing") is None


def test_lru_cache_evicts_oldest() -> None:
    c = _LRUCache(maxsize=2)
    c.set("a", b"1")
    c.set("b", b"2")
    c.set("c", b"3")  # evicts "a"
    assert c.get("a") is None
    assert c.get("b") == b"2"
    assert c.get("c") == b"3"


def test_lru_cache_updates_recency_on_get() -> None:
    c = _LRUCache(maxsize=2)
    c.set("a", b"1")
    c.set("b", b"2")
    c.get("a")        # touch "a" → now most recent
    c.set("c", b"3")  # evicts "b" (least recent)
    assert c.get("a") == b"1"
    assert c.get("b") is None


# ─── PiperTTS — binary/voice checks ──────────────────────────────────────────

def test_piper_raises_when_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPER_VOICE", "/path/to/voice.onnx")
    with patch("runtime.media.tts_service.shutil.which", return_value=None):
        tts = PiperTTS()
        with pytest.raises(PiperNotFoundError, match="piper binary not found"):
            asyncio.run(tts.synthesize("hello"))


def test_piper_raises_when_voice_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIPER_VOICE", raising=False)
    with patch("runtime.media.tts_service.shutil.which", return_value="/usr/bin/piper"):
        tts = PiperTTS()
        with pytest.raises(PiperNotFoundError, match="PIPER_VOICE"):
            asyncio.run(tts.synthesize("hello"))


# ─── PiperTTS — cache ─────────────────────────────────────────────────────────

def _make_wav(sample_rate: int = 22050, n_samples: int = 100) -> bytes:
    """Create a minimal valid WAV file for testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_samples}h", *([0] * n_samples)))
    return buf.getvalue()


def test_piper_cache_hit_skips_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second synthesize() call for same text must NOT spawn a new subprocess."""
    monkeypatch.setenv("PIPER_BINARY", "/usr/bin/piper")
    monkeypatch.setenv("PIPER_VOICE", "/voice.onnx")

    fake_wav = _make_wav()

    async def go():
        tts = PiperTTS()
        with patch.object(tts, "_run_piper", new_callable=AsyncMock, return_value=fake_wav) as mock_run:
            await tts.synthesize("press one")
            await tts.synthesize("press one")  # second call — cache hit
        assert mock_run.call_count == 1  # subprocess only once

    asyncio.run(go())


def test_piper_cache_miss_runs_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIPER_BINARY", "/usr/bin/piper")
    monkeypatch.setenv("PIPER_VOICE", "/voice.onnx")

    fake_wav = _make_wav()

    async def go():
        tts = PiperTTS()
        with patch.object(tts, "_run_piper", new_callable=AsyncMock, return_value=fake_wav) as mock_run:
            await tts.synthesize("press one")
            await tts.synthesize("press two")  # different text → new subprocess
        assert mock_run.call_count == 2

    asyncio.run(go())


# ─── WAV → mulaw conversion ───────────────────────────────────────────────────

def test_wav_to_mulaw8k_returns_bytes() -> None:
    wav = _make_wav(sample_rate=22050, n_samples=220)
    result = PiperTTS._wav_to_mulaw8k(wav)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_wav_to_mulaw8k_8khz_input_passthrough() -> None:
    """8kHz WAV input should not be resampled (already target rate)."""
    wav = _make_wav(sample_rate=8000, n_samples=80)
    result = PiperTTS._wav_to_mulaw8k(wav)
    # mulaw = 1 byte/sample; expect ~80 bytes out from 80 samples in
    assert 70 <= len(result) <= 90


def test_wav_to_mulaw8k_reduces_size_from_22khz() -> None:
    """Resampling from 22050 to 8000 Hz should reduce byte count."""
    wav_22k = _make_wav(sample_rate=22050, n_samples=2205)  # 100ms of audio
    result_22k = PiperTTS._wav_to_mulaw8k(wav_22k)
    # 22kHz result should be approximately 8/22 of the 22kHz sample count
    assert len(result_22k) < 2205  # fewer than original samples