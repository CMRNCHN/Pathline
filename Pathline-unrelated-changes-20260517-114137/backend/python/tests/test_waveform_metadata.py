import struct
import wave
from types import SimpleNamespace

from ivr_assessor.events.waveform_metadata import WaveformService


class _ReplayService:
    def __init__(self, state=None):
        self.state = state

    def load_replay(self, session_id):
        return self.state


def test_waveform_service_returns_missing_when_media_is_absent():
    service = WaveformService(replay_service=_ReplayService())

    payload = service.get_waveform_for_session("missing-session").as_dict()

    assert payload["status"] == "missing"
    assert payload["peaks"] == []
    assert payload["rms_buckets"] == []
    assert payload["duration_ms"] == 0
    assert "missing-session" in payload["reason"]


def test_waveform_service_generates_deterministic_buckets_for_call_wav(tmp_path, monkeypatch):
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    wav_path = recordings_dir / "CALL_WAVE.wav"
    _write_pcm16_wav(wav_path, [1000] * 800 + [16000] * 800)
    monkeypatch.setenv("IVR_RECORDINGS_DIR", str(recordings_dir))

    state = SimpleNamespace(call_sid="CALL_WAVE", recording_reference=None)
    service = WaveformService(replay_service=_ReplayService(state))

    payload = service.get_waveform_for_session("session-wave").as_dict()

    assert payload["status"] == "ready"
    assert payload["bucket_size_ms"] == 100
    assert payload["duration_ms"] == 200
    assert len(payload["peaks"]) == 2
    assert len(payload["rms_buckets"]) == 2
    assert payload["peaks"][0] == round(1000 / 32768, 6)
    assert payload["peaks"][1] == round(16000 / 32768, 6)
    assert payload["rms_buckets"][1] > payload["rms_buckets"][0]


def test_waveform_service_falls_back_for_unreadable_wav(tmp_path, monkeypatch):
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    (recordings_dir / "bad-session.wav").write_bytes(b"not-a-wav")
    monkeypatch.setenv("IVR_RECORDINGS_DIR", str(recordings_dir))

    service = WaveformService(replay_service=_ReplayService())

    payload = service.get_waveform_for_session("bad-session").as_dict()

    assert payload["status"] == "unavailable"
    assert payload["peaks"] == []
    assert payload["rms_buckets"] == []


def _write_pcm16_wav(path, samples):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
