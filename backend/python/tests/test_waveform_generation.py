import pytest
import wave
import struct
import os
from pathlib import Path
from ivr_assessor.events.waveform_metadata import WaveformService, WaveformMetadata

def create_mock_wav(path: Path, duration_sec: float = 1.0):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        n_frames = int(8000 * duration_sec)
        for i in range(n_frames):
            # Sine wave
            sample = int(10000 * (i % 100 / 100.0))
            w.writeframes(struct.pack('<h', sample))

def test_waveform_generation(tmp_path, monkeypatch):
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    date_dir = rec_dir / "2024-01-01"
    date_dir.mkdir()
    rec_file = date_dir / "session_test_wf.wav"
    create_mock_wav(rec_file, duration_sec=2.0)
    
    wf_dir = tmp_path / "waveforms"
    wf_dir.mkdir()
    
    monkeypatch.setattr("ivr_assessor.events.waveform_metadata.RECORDINGS_DIR", rec_dir)
    monkeypatch.setattr("ivr_assessor.events.waveform_metadata.WAVEFORMS_DIR", wf_dir)
    
    service = WaveformService()
    metadata = service.generate_waveform("test_wf")
    
    assert metadata is not None
    assert metadata.duration_ms == 2000
    assert len(metadata.peaks) > 0
    assert len(metadata.rms_buckets) == len(metadata.peaks)
    
    # Verify persistence
    wf_file = wf_dir / "session_test_wf.json"
    assert wf_file.exists()
    
    # Test retrieval
    retrieved = service.get_waveform_for_session("test_wf")
    assert retrieved.duration_ms == 2000
    assert retrieved.peaks == metadata.peaks
