import pytest
import json
from pathlib import Path
from ivr_assessor.events.replay_service import ReplayService
from ivr_assessor.events.snapshot_service import SnapshotService

def create_event_log(path: Path):
    events = []
    ts = 1700000000.0
    # Add a CALL_STARTED event first to establish created_at
    events.append({
        "type": "CALL_STARTED",
        "meta": {"timestamp": ts, "event_id": "e0"},
        "payload": {"call_sid": "sid1"},
        "ts": ts
    })
    for i in range(1, 21):
        events.append({
            "type": "DUMMY", 
            "meta": {"timestamp": ts + i, "event_id": f"e{i}"}, 
            "payload": {},
            "ts": ts + i
        })
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

def test_replay_seek_equivalence(tmp_path, monkeypatch):
    # Setup directories
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    date_dir = events_dir / "2024-01-01"
    date_dir.mkdir()
    session_file = date_dir / "session_equiv.jsonl"
    create_event_log(session_file)
    
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()
    
    monkeypatch.setattr("ivr_assessor.events.replay_service.EVENTS_DIR", events_dir)
    monkeypatch.setattr("ivr_assessor.events.snapshot_service.SNAPSHOTS_DIR", snapshots_dir)
    
    service = ReplayService(events_dir=events_dir)
    
    # Load state at offset 15 normally
    state_normal = service.load_replay("equiv", offset=15)
    
    # Create snapshot at offset 10
    state_10 = service.load_replay("equiv", offset=10)
    snapshot_service = SnapshotService()
    snapshot = snapshot_service.create_snapshot(state_10, event_offset=10)
    snapshot_service.persist_snapshot(snapshot)
    
    # Load state at offset 15 again (should use snapshot)
    state_from_snapshot = service.load_replay("equiv", offset=15)
    
    assert state_from_snapshot.metrics["reconstructed_from_snapshot"] is True
    assert state_from_snapshot.metrics["snapshot_offset"] == 10
    
    # States should be equivalent (ignoring reconstruction metrics)
    dict_normal = state_normal.as_dict()
    dict_snapshot = state_from_snapshot.as_dict()
    
    # Compare core fields
    for field in ["session_id", "nodes", "edges", "transcripts", "dtmf_history"]:
        assert dict_normal[field] == dict_snapshot[field]
    
    assert len(state_normal.events) == len(state_from_snapshot.events)
