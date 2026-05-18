# cspell:ignore audioop mulaw webrtcvad pcm16 ratecv ulaw2lin lin2ulaw
"""Audio preprocessing pipeline for Twilio μ-law media streams.

Packet math (Twilio → 16kHz PCM):
    160 bytes  mulaw  8kHz  20ms  (one Twilio media packet)
  → 320 bytes  PCM16  8kHz  20ms  (ulaw2lin: 2 bytes per sample)
  → 640 bytes  PCM16  16kHz 20ms  (ratecv 8k→16k: 2× sample count)

One Twilio packet = exactly one 20ms VAD frame. No partial-frame buffering needed.
"""
from __future__ import annotations

import importlib
import logging
import sys
import time
import warnings
from typing import Callable

logger = logging.getLogger(__name__)


def _load_audioop():
    if sys.version_info >= (3, 13):
        try:
            return importlib.import_module("audioop")
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "Python 3.13+ requires 'audioop-lts' because stdlib 'audioop' was removed. "
                "Install with: pip install audioop-lts"
            ) from exc

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=DeprecationWarning,
            message=r"'audioop' is deprecated",
        )
        try:
            return importlib.import_module("audioop")
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "Unable to import 'audioop'. Install with: pip install audioop-lts"
            )


audioop = _load_audioop()


try:
    import webrtcvad as _webrtcvad  # type: ignore[import]
except ImportError:
    _webrtcvad = None  # type: ignore[assignment]


def mulaw_to_pcm16(audio_bytes: bytes) -> bytes:
    """Convert μ-law compressed bytes to 16-bit signed PCM.

    160 bytes mulaw (8kHz, 20ms) → 320 bytes PCM16 (8kHz, 20ms).
    """
    return audioop.ulaw2lin(audio_bytes, 2)


def resample_8k_to_16k(pcm16_8k: bytes, state: object = None) -> tuple[bytes, object]:
    """Upsample 8kHz int16 PCM to 16kHz via linear interpolation.

    Returns (resampled_bytes, new_state). Pass state between calls for a
    continuous stream; pass None for isolated frames (state is discarded).

    320 bytes PCM16 8kHz → 640 bytes PCM16 16kHz.
    """
    resampled, new_state = audioop.ratecv(pcm16_8k, 2, 1, 8000, 16000, state)
    return resampled, new_state


_SILENCE_RMS_FLOOR = 20 / 32768
_MAX_GAIN = 4.0
_TARGET_RMS = 32768 * (10 ** (-3 / 20))


def normalize_pcm(pcm16: bytes) -> bytes:
    """Normalize PCM volume to -3 dBFS, clip-safe."""
    if not pcm16:
        return pcm16

    rms = audioop.rms(pcm16, 2) / 32768
    if rms < _SILENCE_RMS_FLOOR:
        return pcm16

    gain = min(_TARGET_RMS / (rms * 32768), _MAX_GAIN)
    if abs(gain - 1.0) < 0.02:
        return pcm16

    return audioop.mul(pcm16, 2, gain)


def process_audio_frame(mulaw_bytes: bytes) -> bytes:
    """One-call pipeline: μ-law 8kHz → normalized PCM16 16kHz."""
    pcm8k = mulaw_to_pcm16(mulaw_bytes)
    pcm16k, _ = resample_8k_to_16k(pcm8k)
    return normalize_pcm(pcm16k)


class VoiceActivityDetector:
    """Accumulates 16kHz PCM16 frames, emits complete utterances via callback."""

    def __init__(
        self,
        on_utterance: Callable[[bytes], None],
        aggressiveness: int = 2,
        silence_ms: int = 800,
        max_utterance_ms: int = 10_000,
    ) -> None:
        self.on_utterance = on_utterance
        self.silence_ms = silence_ms
        self.max_utterance_ms = max_utterance_ms
        self._buffer = bytearray()
        self._speech_started_at: float | None = None
        self._last_speech_at: float | None = None

        if _webrtcvad is None:
            self._vad = None
            logger.warning("webrtcvad not installed; VAD disabled")
        else:
            self._vad = _webrtcvad.Vad(aggressiveness)

    def add_frame(self, pcm16_16k: bytes) -> None:
        if not pcm16_16k:
            return

        now = time.time()
        is_speech = True
        if self._vad is not None:
            is_speech = self._vad.is_speech(pcm16_16k, 16000)

        if is_speech:
            if self._speech_started_at is None:
                self._speech_started_at = now
            self._last_speech_at = now
            self._buffer.extend(pcm16_16k)
            return

        if self._speech_started_at is None:
            return

        self._buffer.extend(pcm16_16k)

        silence_elapsed_ms = (
            0 if self._last_speech_at is None else int((now - self._last_speech_at) * 1000)
        )
        utterance_elapsed_ms = int((now - self._speech_started_at) * 1000)

        if silence_elapsed_ms >= self.silence_ms or utterance_elapsed_ms >= self.max_utterance_ms:
            self.flush()

    def flush(self) -> None:
        if self._buffer:
            self.on_utterance(bytes(self._buffer))
        self._buffer.clear()
        self._speech_started_at = None
        self._last_speech_at = None
