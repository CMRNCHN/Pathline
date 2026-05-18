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

# ─── audioop shim ────────────────────────────────────────────────────────────
# audioop was deprecated in Python 3.12 and removed in 3.13.
# audioop-lts provides the identical C extension API for 3.13+.
def _load_audioop():
    if sys.version_info >= (3, 13):
        try:
            return importlib.import_module("audioop_lts")
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
            try:
                return importlib.import_module("audioop_lts")
            except ModuleNotFoundError as exc:
                raise ModuleNotFoundError(
                    "Unable to import 'audioop' on Python <3.13 and fallback "
                    "'audioop-lts' is also unavailable. Install with: pip install audioop-lts"
                ) from exc

audioop = _load_audioop()


# ─── webrtcvad shim ──────────────────────────────────────────────────────────
try:
    import webrtcvad as _webrtcvad  # type: ignore[import]
except ImportError:
    _webrtcvad = None  # type: ignore[assignment]


# ─── Audio conversion helpers ─────────────────────────────────────────────────

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


_SILENCE_RMS_FLOOR = 20 / 32768  # below this, treat as silence — skip gain
_MAX_GAIN = 4.0                   # cap to avoid over-amplification of whispers
_TARGET_RMS = 32768 * (10 ** (-3 / 20))  # -3 dBFS ≈ 23197


def normalize_pcm(pcm16: bytes) -> bytes:
    """Normalize PCM volume to -3 dBFS, clip-safe.

    Skips frames below a silence floor to avoid amplifying noise.
    Caps gain at 4× to prevent extreme amplification of very quiet speech.
    """
    if not pcm16:
        return pcm16

    rms = audioop.rms(pcm16, 2) / 32768
    if rms < _SILENCE_RMS_FLOOR:
        return pcm16

    gain = min(_TARGET_RMS / (rms * 32768), _MAX_GAIN)
    if abs(gain - 1.0) < 0.02:  # skip tiny adjustments
        return pcm16

    # audioop.mul applies gain; audioop.bias clips implicitly at int16 range
    # but we must scale carefully to avoid distortion.
    # Use audioop.mul which clamps at int16 bounds.
    scaled = audioop.mul(pcm16, 2, gain)
    return scaled


def process_audio_frame(mulaw_bytes: bytes) -> bytes:
    """One-call pipeline: μ-law 8kHz → normalized PCM16 16kHz.

    Input:  160 bytes mulaw (one 20ms Twilio packet)
    Output: 640 bytes PCM16 at 16kHz
    """
    pcm8k = mulaw_to_pcm16(mulaw_bytes)
    pcm16k, _ = resample_8k_to_16k(pcm8k)
    return normalize_pcm(pcm16k)


# ─── Voice Activity Detector ──────────────────────────────────────────────────

class VoiceActivityDetector:
    """Accumulates 16kHz PCM16 frames, emits complete utterances via callback.

    Frame contract:
        Each call to feed() must supply exactly FRAME_BYTES (640) bytes —
        one 20ms frame at 16kHz int16. Twilio packets satisfy this exactly
        after process_audio_frame().

    Silence detection:
        SILENCE_FRAMES_THRESHOLD consecutive silent frames (300ms) triggers
        utterance emission if speech was detected in the buffer.

    Hard cap:
        MAX_SPEECH_FRAMES (1500 = 30s) forces emission regardless of silence.

    on_utterance receives the concatenated PCM16 bytes of the full utterance.
    It is called synchronously from feed() / flush() — wrap with
    asyncio.ensure_future if the transcriber is async.
    """

    SAMPLE_RATE = 16000
    FRAME_MS = 20
    FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000   # 320 samples
    FRAME_BYTES = FRAME_SAMPLES * 2                   # 640 bytes (int16)

    SILENCE_FRAMES_THRESHOLD = 15    # 300ms silence → emit utterance
    MAX_SPEECH_FRAMES = 1500         # 30s hard cap

    def __init__(
        self,
        on_utterance: Callable[[bytes], None],
        mode: int = 1,
    ) -> None:
        """
        mode: webrtcvad aggressiveness 0–3 (0=least, 3=most aggressive filtering).
              1 = medium — good balance for telephone speech.
        """
        if _webrtcvad is None:
            raise ImportError(
                "webrtcvad not installed. Run: pip install webrtcvad"
            )
        self._vad = _webrtcvad.Vad(mode)

        self._on_utterance = on_utterance
        self._speech_buffer: list[bytes] = []
        self._silent_frames = 0
        self._in_speech = False
        self._frames_seen = 0
        self._speech_frames_seen = 0
        self._silence_frames_seen = 0
        self._dropped_malformed_frames = 0
        self._utterances_emitted = 0
        self._max_buffered_frames = 0
        self._last_emit_reason = ""
        self._last_utterance_frames = 0
        self._last_utterance_ms = 0
        self._last_emit_at: float | None = None

    def feed(self, pcm16_bytes: bytes) -> None:
        """Accept one 20ms PCM16 16kHz frame (must be exactly FRAME_BYTES bytes)."""
        self._frames_seen += 1
        if len(pcm16_bytes) != self.FRAME_BYTES:
            # Silently drop malformed frames — log at debug only to avoid spam
            self._dropped_malformed_frames += 1
            logger.debug(
                "VAD: dropping frame with unexpected size %d (expected %d)",
                len(pcm16_bytes),
                self.FRAME_BYTES,
            )
            return

        try:
            is_speech = self._vad.is_speech(pcm16_bytes, self.SAMPLE_RATE)
        except Exception as exc:
            logger.debug("VAD: is_speech error: %s", exc)
            return

        if is_speech:
            self._speech_frames_seen += 1
            self._speech_buffer.append(pcm16_bytes)
            self._silent_frames = 0
            self._in_speech = True
            self._max_buffered_frames = max(self._max_buffered_frames, len(self._speech_buffer))

            if len(self._speech_buffer) >= self.MAX_SPEECH_FRAMES:
                logger.debug("VAD: hard cap reached, forcing utterance emit")
                self._emit("hard_cap")
        else:
            self._silence_frames_seen += 1
            if self._in_speech:
                self._speech_buffer.append(pcm16_bytes)  # include trailing silence
                self._silent_frames += 1
                self._max_buffered_frames = max(self._max_buffered_frames, len(self._speech_buffer))
                if self._silent_frames >= self.SILENCE_FRAMES_THRESHOLD:
                    self._emit("silence")

    def flush(self) -> None:
        """Force-emit any buffered speech. Call on stream end."""
        if self._speech_buffer:
            logger.debug("VAD: flush emitting %d buffered frames", len(self._speech_buffer))
            self._emit("flush")

    def reset(self) -> None:
        """Clear all state — call between calls."""
        self._speech_buffer.clear()
        self._silent_frames = 0
        self._in_speech = False

    def _emit(self, reason: str) -> None:
        utterance = b"".join(self._speech_buffer)
        frame_count = len(self._speech_buffer)
        self._speech_buffer.clear()
        self._silent_frames = 0
        self._in_speech = False
        self._utterances_emitted += 1
        self._last_emit_reason = reason
        self._last_utterance_frames = frame_count
        self._last_utterance_ms = frame_count * self.FRAME_MS
        self._last_emit_at = time.monotonic()
        try:
            self._on_utterance(utterance)
        except Exception as exc:
            logger.error("VAD: on_utterance callback raised: %s", exc, exc_info=True)

    def stats(self) -> dict[str, int | str | None]:
        return {
            "frames_seen": self._frames_seen,
            "speech_frames_seen": self._speech_frames_seen,
            "silence_frames_seen": self._silence_frames_seen,
            "dropped_malformed_frames": self._dropped_malformed_frames,
            "utterances_emitted": self._utterances_emitted,
            "max_buffered_frames": self._max_buffered_frames,
            "buffered_frames": len(self._speech_buffer),
            "last_emit_reason": self._last_emit_reason,
            "last_utterance_frames": self._last_utterance_frames,
            "last_utterance_ms": self._last_utterance_ms,
            "last_emit_at": self._last_emit_at,
        }
