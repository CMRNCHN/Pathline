from __future__ import annotations

import math
import os
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import audioop  # type: ignore[import]
except ImportError:  # pragma: no cover - exercised on Python 3.13 without audioop-lts.
    audioop = None  # type: ignore[assignment]

from ..backend.ui.ui_state import RECORDINGS_DIR, REPORTS_DIR
from .replay_service import ReplayService

@dataclass
class WaveformMetadata:
    """
    Lightweight summary of audio energy peaks for visualization.
    """
    peaks: List[float] = field(default_factory=list)  # Normalised peaks (0.0 to 1.0)
    rms_buckets: List[float] = field(default_factory=list) # RMS energy levels
    bucket_size_ms: int = 100
    duration_ms: int = 0
    status: str = "missing"
    reason: str = "recording_not_found"
    
    def as_dict(self) -> Dict[str, Any]:
        return {
            "peaks": self.peaks,
            "rms_buckets": self.rms_buckets,
            "bucket_size_ms": self.bucket_size_ms,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "reason": self.reason,
        }

class WaveformService:
    """
    Generate bounded waveform metadata from local replay WAV recordings.
    """
    def __init__(
        self,
        replay_service: ReplayService | None = None,
        *,
        bucket_size_ms: int = 100,
        max_buckets: int = 2000,
    ) -> None:
        self.replay_service = replay_service or ReplayService()
        self.bucket_size_ms = max(1, bucket_size_ms)
        self.max_buckets = max(1, max_buckets)

    def get_waveform_for_session(self, session_id: str) -> Optional[WaveformMetadata]:
        media_path = self._resolve_media_path(session_id)
        if not media_path:
            return self._missing(session_id)

        try:
            return self._build_waveform(media_path)
        except (wave.Error, OSError, EOFError, ValueError):
            return WaveformMetadata(
                peaks=[],
                rms_buckets=[],
                bucket_size_ms=self.bucket_size_ms,
                duration_ms=0,
                status="unavailable",
                reason=f"waveform metadata unavailable for session {session_id}",
            )

    def _missing(self, session_id: str) -> WaveformMetadata:
        return WaveformMetadata(
            peaks=[],
            rms_buckets=[],
            bucket_size_ms=self.bucket_size_ms,
            duration_ms=0,
            status="missing",
            reason=f"no waveform metadata for session {session_id}",
        )

    def _build_waveform(self, media_path: Path) -> WaveformMetadata:
        with wave.open(str(media_path), "rb") as wav:
            frame_rate = wav.getframerate()
            frame_count = wav.getnframes()
            sample_width = wav.getsampwidth()
            channels = wav.getnchannels()

            if frame_rate <= 0 or sample_width not in (1, 2, 3, 4) or channels <= 0:
                raise ValueError("unsupported wav parameters")

            duration_ms = int(round((frame_count / frame_rate) * 1000)) if frame_count else 0
            bucket_size_ms = self._bucket_size_ms(duration_ms)
            frames_per_bucket = max(1, int(round(frame_rate * bucket_size_ms / 1000)))
            bucket_count = math.ceil(frame_count / frames_per_bucket) if frame_count else 0

            peaks: list[float] = []
            rms_buckets: list[float] = []
            for _ in range(bucket_count):
                frames = wav.readframes(frames_per_bucket)
                if not frames:
                    break
                peak, rms = _normalised_stats(frames, sample_width, channels)
                peaks.append(peak)
                rms_buckets.append(rms)

        return WaveformMetadata(
            peaks=peaks,
            rms_buckets=rms_buckets,
            bucket_size_ms=bucket_size_ms,
            duration_ms=duration_ms,
            status="ready",
            reason="waveform_metadata_generated",
        )

    def _bucket_size_ms(self, duration_ms: int) -> int:
        if duration_ms <= 0:
            return self.bucket_size_ms
        estimated_buckets = math.ceil(duration_ms / self.bucket_size_ms)
        if estimated_buckets <= self.max_buckets:
            return self.bucket_size_ms
        return int(math.ceil(duration_ms / self.max_buckets))

    def _resolve_media_path(self, session_id: str) -> Path | None:
        call_sid = None
        recording_reference = None
        state = self.replay_service.load_replay(session_id)
        if state:
            call_sid = state.call_sid
            recording_reference = state.recording_reference

        roots = [
            Path(os.environ.get("IVR_RECORDINGS_DIR", str(RECORDINGS_DIR))).expanduser(),
            RECORDINGS_DIR,
            Path(os.environ.get("IVR_REPORTS_DIR", str(REPORTS_DIR))).expanduser() / "recordings",
            REPORTS_DIR / "recordings",
        ]
        for name in _candidate_media_names(session_id, call_sid, recording_reference):
            candidate = Path(name)
            if candidate.is_absolute() and candidate.is_file():
                return candidate
            for root in roots:
                path = root / name
                if path.is_file():
                    return path
        return None


def _candidate_media_names(
    session_id: str,
    call_sid: str | None,
    recording_reference: str | None,
) -> list[str]:
    names: list[str] = []
    for value in (session_id, call_sid, recording_reference):
        if not value:
            continue
        path = Path(str(value))
        if path.is_absolute():
            absolute_name = str(path)
            if absolute_name not in names:
                names.append(absolute_name)
        stem = path.name
        if stem and stem not in names:
            names.append(stem)
        if stem and not stem.endswith(".wav"):
            wav_name = f"{stem}.wav"
            if wav_name not in names:
                names.append(wav_name)
    return names


def _normalised_stats(frames: bytes, sample_width: int, channels: int) -> tuple[float, float]:
    if audioop is not None and sample_width != 1:
        max_sample = float(1 << (sample_width * 8 - 1))
        return (
            _clamp_unit(audioop.max(frames, sample_width) / max_sample),
            _clamp_unit(audioop.rms(frames, sample_width) / max_sample),
        )
    return _manual_normalised_stats(frames, sample_width, channels)


def _manual_normalised_stats(frames: bytes, sample_width: int, channels: int) -> tuple[float, float]:
    frame_width = sample_width * channels
    if frame_width <= 0:
        raise ValueError("invalid wav frame width")

    sample_limit = float(1 << (sample_width * 8 - 1))
    peak = 0.0
    square_sum = 0.0
    sample_count = 0

    usable_bytes = len(frames) - (len(frames) % sample_width)
    for index in range(0, usable_bytes, sample_width):
        raw = frames[index:index + sample_width]
        sample = _decode_sample(raw, sample_width)
        peak = max(peak, abs(sample))
        square_sum += float(sample * sample)
        sample_count += 1

    if sample_count == 0:
        return 0.0, 0.0

    rms = math.sqrt(square_sum / sample_count)
    return _clamp_unit(peak / sample_limit), _clamp_unit(rms / sample_limit)


def _decode_sample(raw: bytes, sample_width: int) -> int:
    if sample_width == 1:
        return raw[0] - 128
    if sample_width == 3:
        sign = b"\xff" if raw[2] & 0x80 else b"\x00"
        return int.from_bytes(raw + sign, "little", signed=True)
    return int.from_bytes(raw, "little", signed=True)


def _clamp_unit(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)
