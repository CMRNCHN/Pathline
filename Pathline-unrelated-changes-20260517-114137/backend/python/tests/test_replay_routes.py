import json

import pytest

from ivr_assessor.backend.routes import replay_routes
from ivr_assessor.events.event_types import EventType
from ivr_assessor.events.replay_service import ReplayService
from ivr_assessor.events.waveform_metadata import WaveformService


@pytest.fixture
def replay_route_service(tmp_path, monkeypatch):
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    date_dir = events_dir / "2026-05-15"
    date_dir.mkdir()
    session_id = "route-session"
    session_file = date_dir / f"session_{session_id}.jsonl"
    events = [
        {"type": EventType.CALL_STARTED, "payload": {"call_sid": "CALL_ROUTE"}, "meta": {"timestamp": 1000.0, "event_id": "e1"}},
        {"type": EventType.TRANSCRIPT_FINAL, "payload": {"text": "Press 1", "speech_start_offset": 1.5}, "meta": {"timestamp": 1001.5, "event_id": "e2"}},
        {"type": EventType.DTMF_SENT, "payload": {"digits": "1"}, "meta": {"timestamp": 1003.0, "event_id": "e3"}},
    ]
    with open(session_file, "w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")

    monkeypatch.setattr(replay_routes, "_replay_service", ReplayService(events_dir=events_dir))
    monkeypatch.setattr(replay_routes, "_waveform_service", WaveformService())
    return session_id


def test_replay_route_raises_404_for_missing_session():
    with pytest.raises(FileNotFoundError):
        replay_routes.get_replay("missing-session")


def test_replay_route_rejects_out_of_bounds_offset(replay_route_service):
    with pytest.raises(ValueError):
        replay_routes.get_replay(replay_route_service, offset=99)


def test_replay_cursor_rejects_negative_offset(replay_route_service):
    with pytest.raises(ValueError):
        replay_routes.get_replay_cursor(replay_route_service, -1)


def test_waveform_route_returns_structured_fallback(replay_route_service):
    payload = replay_routes.get_waveform_metadata(replay_route_service)
    assert payload["session_id"] == replay_route_service
    assert payload["status"] == "missing"
    assert "reason" in payload
    assert payload["media_available"] is False


def test_replay_media_path_resolves_local_recording(replay_route_service, tmp_path, monkeypatch):
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    media_path = recordings_dir / "CALL_ROUTE.wav"
    media_path.write_bytes(b"RIFF-test")
    monkeypatch.setenv("IVR_RECORDINGS_DIR", str(recordings_dir))

    payload = replay_routes.get_waveform_metadata(replay_route_service)

    assert payload["media_available"] is True
    assert payload["media_url"] == f"/api/replays/{replay_route_service}/media"
    assert replay_routes.get_replay_media_path(replay_route_service) == media_path


def test_alignment_route_returns_consistent_payload(replay_route_service):
    payload = replay_routes.get_alignment_lookup(replay_route_service)
    assert payload["session_id"] == replay_route_service
    assert payload["status"] == "ready"
    assert len(payload["items"]) == 3
    assert payload["items"][1]["alignment_source"] == "STT_SPEECH_START"
