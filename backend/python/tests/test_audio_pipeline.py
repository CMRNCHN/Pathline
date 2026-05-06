"""Tests for audio_pipeline.py — mulaw decode, resample, normalize, VAD."""
from __future__ import annotations

import struct
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from ivr_assessor.audio_pipeline import (
    VoiceActivityDetector,
    mulaw_to_pcm16,
    normalize_pcm,
    process_audio_frame,
    resample_8k_to_16k,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _silent_mulaw(n_bytes: int = 160) -> bytes:
    """Return n_bytes of μ-law silence (μ-law value 0xFF = silence)."""
    return bytes([0xFF] * n_bytes)


def _make_pcm16(samples: list[int]) -> bytes:
    """Pack list of int16 samples into bytes."""
    return struct.pack(f"<{len(samples)}h", *samples)


def _make_speech_frame() -> bytes:
    """Return a 640-byte PCM16 16kHz frame that webrtcvad should classify as speech."""
    # A 400Hz sine approximation at moderate volume — not guaranteed speech but
    # sufficient with a mocked VAD (tests mock is_speech anyway).
    import math
    samples = [int(16000 * math.sin(2 * math.pi * 400 * i / 16000)) for i in range(320)]
    return _make_pcm16(samples)


def _make_vad_with_mock(speech_sequence: list[bool], on_utterance=None) -> tuple[VoiceActivityDetector, Any]:
    """Create a VAD with _webrtcvad.Vad mocked to return values from speech_sequence."""
    mock_vad = MagicMock()
    mock_vad.is_speech.side_effect = speech_sequence
    if on_utterance is None:
        on_utterance = MagicMock()

    mock_module = MagicMock()
    mock_module.Vad.return_value = mock_vad
    with patch("ivr_assessor.audio_pipeline._webrtcvad", mock_module):
        vad = VoiceActivityDetector(on_utterance=on_utterance)

    vad._vad = mock_vad  # inject mock directly for feeding frames
    return vad, on_utterance


# ─── mulaw_to_pcm16 ───────────────────────────────────────────────────────────

def test_mulaw_to_pcm16_output_length() -> None:
    """160 bytes mulaw → 320 bytes PCM16 (2 bytes per sample)."""
    result = mulaw_to_pcm16(_silent_mulaw(160))
    assert len(result) == 320


def test_mulaw_to_pcm16_returns_bytes() -> None:
    assert isinstance(mulaw_to_pcm16(_silent_mulaw()), bytes)


# ─── resample_8k_to_16k ───────────────────────────────────────────────────────

def test_resample_doubles_length() -> None:
    """320 bytes PCM16 8kHz → ~640 bytes PCM16 16kHz."""
    pcm8k = mulaw_to_pcm16(_silent_mulaw(160))
    resampled, state = resample_8k_to_16k(pcm8k)
    # audioop.ratecv may produce slightly more samples due to interpolation;
    # allow ±10 bytes tolerance.
    assert abs(len(resampled) - 640) <= 10


def test_resample_returns_state() -> None:
    pcm8k = mulaw_to_pcm16(_silent_mulaw(160))
    _, state = resample_8k_to_16k(pcm8k)
    assert state is not None  # state is an opaque tuple for chaining


# ─── normalize_pcm ────────────────────────────────────────────────────────────

def test_normalize_does_not_clip_near_saturation() -> None:
    """A signal near int16 max must not overflow after normalization."""
    # Near-saturation signal: samples at ±30000
    samples = [30000 if i % 2 == 0 else -30000 for i in range(320)]
    pcm = _make_pcm16(samples)
    result = normalize_pcm(pcm)
    unpacked = struct.unpack(f"<{len(result)//2}h", result)
    assert all(-32768 <= s <= 32767 for s in unpacked), "Sample out of int16 range"


def test_normalize_skips_silent_frame() -> None:
    """All-zero frame is below silence floor — returned unchanged."""
    silent = bytes(640)
    result = normalize_pcm(silent)
    assert result == silent


def test_normalize_returns_bytes() -> None:
    pcm = _make_pcm16([1000] * 320)
    assert isinstance(normalize_pcm(pcm), bytes)


def test_normalize_empty_passthrough() -> None:
    assert normalize_pcm(b"") == b""


# ─── process_audio_frame ──────────────────────────────────────────────────────

def test_process_audio_frame_output_length() -> None:
    """160 bytes mulaw → ~640 bytes PCM16 16kHz after full pipeline."""
    result = process_audio_frame(_silent_mulaw(160))
    assert abs(len(result) - 640) <= 10


def test_process_audio_frame_returns_bytes() -> None:
    assert isinstance(process_audio_frame(_silent_mulaw(160)), bytes)


# ─── VoiceActivityDetector ────────────────────────────────────────────────────

def _feed_sequence(vad: VoiceActivityDetector, speech_flags: list[bool]) -> None:
    """Feed one frame per flag; VAD mock uses speech_flags via side_effect."""
    frame = bytes(VoiceActivityDetector.FRAME_BYTES)
    for _ in speech_flags:
        vad.feed(frame)


def test_vad_emits_utterance_after_silence_threshold() -> None:
    """Speech frames followed by enough silence → on_utterance called once."""
    n_speech = 10
    n_silence = VoiceActivityDetector.SILENCE_FRAMES_THRESHOLD
    flags = [True] * n_speech + [False] * n_silence
    vad, callback = _make_vad_with_mock(flags)
    _feed_sequence(vad, flags)
    callback.assert_called_once()
    emitted: bytes = callback.call_args[0][0]
    # Buffer contains speech + trailing silence frames
    expected_frames = n_speech + n_silence
    assert len(emitted) == expected_frames * VoiceActivityDetector.FRAME_BYTES


def test_vad_does_not_emit_mid_speech() -> None:
    """No emission during continuous speech (silence threshold not reached)."""
    flags = [True] * 20
    vad, callback = _make_vad_with_mock(flags)
    _feed_sequence(vad, flags)
    callback.assert_not_called()


def test_vad_force_emits_at_hard_cap() -> None:
    """MAX_SPEECH_FRAMES of continuous speech triggers forced emission."""
    cap = VoiceActivityDetector.MAX_SPEECH_FRAMES
    flags = [True] * (cap + 5)
    vad, callback = _make_vad_with_mock(flags)
    _feed_sequence(vad, flags)
    assert callback.call_count >= 1
    # First call should be at the cap
    emitted: bytes = callback.call_args_list[0][0][0]
    assert len(emitted) == cap * VoiceActivityDetector.FRAME_BYTES


def test_vad_flush_emits_partial_buffer() -> None:
    """flush() emits whatever is buffered, even without silence."""
    flags = [True] * 5
    vad, callback = _make_vad_with_mock(flags)
    _feed_sequence(vad, flags)
    callback.assert_not_called()
    vad.flush()
    callback.assert_called_once()


def test_vad_flush_on_empty_buffer_is_noop() -> None:
    """flush() on an empty buffer must not raise or call callback."""
    vad, callback = _make_vad_with_mock([])
    vad.flush()  # should be a no-op
    callback.assert_not_called()


def test_vad_reset_clears_state() -> None:
    """After reset(), previously buffered speech is discarded."""
    flags_before = [True] * 5
    vad, callback = _make_vad_with_mock(flags_before + [False] * 20)
    _feed_sequence(vad, flags_before)
    vad.reset()
    # Feed silence — should not emit (buffer was cleared by reset)
    _feed_sequence(vad, [False] * VoiceActivityDetector.SILENCE_FRAMES_THRESHOLD)
    callback.assert_not_called()


def test_vad_drops_malformed_frame() -> None:
    """Frames with wrong byte count are silently dropped (no error, no emission)."""
    vad, callback = _make_vad_with_mock([True] * 5)
    bad_frame = bytes(100)  # not FRAME_BYTES
    for _ in range(5):
        vad.feed(bad_frame)  # should not raise
    callback.assert_not_called()


def test_vad_import_error_raises_clearly() -> None:
    """Missing webrtcvad (None) raises ImportError with a helpful message."""
    with patch("ivr_assessor.audio_pipeline._webrtcvad", None):
        with pytest.raises(ImportError, match="webrtcvad not installed"):
            VoiceActivityDetector(on_utterance=lambda _: None)
