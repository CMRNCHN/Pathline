import json
from pathlib import Path
from replay.timelines.replay_service import ReplayService

def create_event_log(path: Path, session_id: str):
    events = [
        {"type": "CALL_STARTED", "meta": {"timestamp": 1700000000.0, "event_id": "e1"}, "payload": {"call_sid": "sid1"}},
        {"type": "TRANSCRIPT_FINAL", "meta": {"timestamp": 1700000005.0, "event_id": "e2"}, "payload": {"text": "hello", "speech_start_offset": 2.0}},
        {"type": "TRANSCRIPT_FINAL", "meta": {"timestamp": 1700000010.0, "event_id": "e3"}, "payload": {"text": "world", "speech_start_offset": 7.0}},
    ]
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

def test_nearest_event_lookup(tmp_path, monkeypatch):
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    date_dir = events_dir / "2024-01-01"
    date_dir.mkdir()
    session_file = date_dir / "session_test_seek.jsonl"
    create_event_log(session_file, "test_seek")
    
    monkeypatch.setattr("replay.timelines.replay_service.EVENTS_DIR", events_dir)
    
    service = ReplayService(events_dir=events_dir)
    
    # 2500ms should match the first transcript (offset 2000)
    nearest = service.get_nearest_event_for_timestamp("test_seek", 2500)
    assert nearest is not None
    assert nearest["index"] == 1
    assert nearest["event"]["payload"]["text"] == "hello"
    
    # 7500ms should match the second transcript (offset 7000)
    nearest = service.get_nearest_event_for_timestamp("test_seek", 7500)
    assert nearest is not None
    assert nearest["index"] == 2
    assert nearest["event"]["payload"]["text"] == "world"
    
    # 0ms should match CALL_STARTED (offset 0)
    nearest = service.get_nearest_event_for_timestamp("test_seek", 0)
    assert nearest is not None
    assert nearest["index"] == 0

def test_replay_cursor_alignment(tmp_path, monkeypatch):
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    date_dir = events_dir / "2024-01-01"
    date_dir.mkdir()
    session_file = date_dir / "session_test_seek.jsonl"
    create_event_log(session_file, "test_seek")
    
    monkeypatch.setattr("replay.timelines.replay_service.EVENTS_DIR", events_dir)
    service = ReplayService(events_dir=events_dir)
    
    cursor = service.get_cursor_for_time("test_seek", 5000)
    assert cursor is not None
    assert cursor["event_index"] == 1
    assert cursor["media_time_ms"] == 5000
    assert cursor["active_event_index"] == 1