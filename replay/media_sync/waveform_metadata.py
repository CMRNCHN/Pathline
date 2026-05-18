import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from analyst.backend.ui.ui_state import WAVEFORMS_DIR, RECORDINGS_DIR

@dataclass
class WaveformMetadata:
    """
    Lightweight summary of audio energy peaks for visualization.
    """
    peaks: List[float] = field(default_factory=list)  # Normalised peaks (0.0 to 1.0)
    rms_buckets: List[float] = field(default_factory=list) # RMS energy levels
    bucket_size_ms: int = 100
    duration_ms: int = 0
    
    def as_dict(self) -> Dict[str, Any]:
        return {
            "peaks": self.peaks,
            "rms_buckets": self.rms_buckets,
            "bucket_size_ms": self.bucket_size_ms,
            "duration_ms": self.duration_ms
        }

class WaveformService:
    """
    Foundation for waveform metadata retrieval and generation.
    Supports chunked loading (future) and deterministic regeneration.
    """
    def get_waveform_for_session(self, session_id: str) -> Optional[WaveformMetadata]:
        """
        Retrieves waveform metadata from disk or generates it if missing.
        """
        path = self._get_waveform_path(session_id)
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    return WaveformMetadata(
                        peaks=data.get("peaks", []),
                        rms_buckets=data.get("rms_buckets", []),
                        bucket_size_ms=data.get("bucket_size_ms", 100),
                        duration_ms=data.get("duration_ms", 0)
                    )
            except Exception:
                pass
        
        # Try to generate if recording exists
        return self.generate_waveform(session_id)

    def generate_waveform(self, session_id: str) -> Optional[WaveformMetadata]:
        """
        Generates waveform metadata from the recording.
        Currently a lightweight implementation.
        """
        recording_path = self._resolve_recording_path(session_id)
        if not recording_path or not recording_path.exists():
            return None
            
        # For now, we'll implement a VERY lightweight placeholder generation 
        # that mimics what a real processor would do without heavy dependencies.
        # In a real scenario, we'd use wave or soundfile.
        
        try:
            import wave
            import struct
            
            with wave.open(str(recording_path), 'rb') as w:
                n_channels = w.getnchannels()
                sample_width = w.getsampwidth()
                frame_rate = w.getframerate()
                n_frames = w.getnframes()
                
                duration_ms = int((n_frames / frame_rate) * 1000)
                bucket_size_ms = 100
                frames_per_bucket = int((bucket_size_ms / 1000.0) * frame_rate)
                
                peaks = []
                rms_buckets = []
                
                for i in range(0, n_frames, frames_per_bucket):
                    chunk = w.readframes(frames_per_bucket)
                    if not chunk:
                        break
                        
                    # Basic peak/RMS calculation for 16-bit PCM
                    if sample_width == 2:
                        fmt = f"<{len(chunk)//2}h"
                        samples = struct.unpack(fmt, chunk)
                        if samples:
                            peak = max(abs(s) for s in samples) / 32768.0
                            rms = (sum(s*s for s in samples) / len(samples))**0.5 / 32768.0
                            peaks.append(round(peak, 3))
                            rms_buckets.append(round(rms, 3))
                
                metadata = WaveformMetadata(
                    peaks=peaks,
                    rms_buckets=rms_buckets,
                    bucket_size_ms=bucket_size_ms,
                    duration_ms=duration_ms
                )
                
                # Persist it
                self._save_waveform(session_id, metadata)
                return metadata
        except Exception:
            # Fallback if wave fails or file is not found
            return None

    def _get_waveform_path(self, session_id: str) -> Path:
        # Partitioned by date? Let's keep it simple for now or match RECORDINGS_DIR structure
        # Since we search RECORDINGS_DIR recursively, we might need a way to find where to save.
        # Let's use a flat structure under WAVEFORMS_DIR for now or derive from session_id
        return WAVEFORMS_DIR / f"session_{session_id}.json"

    def _save_waveform(self, session_id: str, metadata: WaveformMetadata):
        path = self._get_waveform_path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(metadata.as_dict(), f)

    def _resolve_recording_path(self, session_id: str) -> Optional[Path]:
        for path in RECORDINGS_DIR.rglob(f"session_{session_id}.wav"):
            return path
        return None