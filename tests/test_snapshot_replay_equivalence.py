import pytest
import json
from runtime.events.event_types import EventType
from replay.timelines.replay_service import ReplayService
from replay.snapshots.snapshot_service import SnapshotService
from replay.reducers.replay_reducer import apply_event
from runtime.state.replay_state import ReplayState

@pytest.fixture
def temp_dirs(tmp_path):
    events_dir = tmp_path / "events"
    snapshots_dir = tmp_path / "snapshots"
    events_dir.mkdir()
    snapshots_dir.mkdir()
    return events_dir, snapshots_dir

def test_replay_equivalence(temp_dirs):
    events_dir, snapshots_dir = temp_dirs
    session_id = "equiv_test"
    date_str = "2026-05-13"
    session_file = events_dir / date_str / f"session_{session_id}.jsonl"
    session_file.parent.mkdir(parents=True)
    
    # 1. Create a stream of events
    events = [
        {"type": EventType.CALL_STARTED, "payload": {"call_sid": "sid1"}, "meta": {"timestamp": 1000, "session_id": session_id}},
        {"type": EventType.NODE_DISCOVERED, "payload": {"id": "N1"}, "meta": {"timestamp": 1001, "session_id": session_id}},
        {"type": EventType.NODE_DISCOVERED, "payload": {"id": "N2"}, "meta": {"timestamp": 1002, "session_id": session_id}},
        {"type": EventType.DTMF_SENT, "payload": {"digits": "1"}, "meta": {"timestamp": 1003, "session_id": session_id}},
        {"type": EventType.CALL_COMPLETED, "payload": {}, "meta": {"timestamp": 1004, "session_id": session_id}},
    ]
    
    with open(session_file, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
            
    # 2. ReplayService (Full Replay)
    service = ReplayService(events_dir=events_dir)
    service.snapshot_service = SnapshotService(snapshots_dir=snapshots_dir)
    
    full_state = service.load_replay(session_id)
    assert full_state.metrics["reconstructed_from_snapshot"] is False
    
    # 3. Create a snapshot manually at offset 2 (after N1)
    state_at_2 = ReplayState(session_id=session_id)
    for e in events[:2]:
        state_at_2 = apply_event(state_at_2, e)
        
    snapshot = service.snapshot_service.create_snapshot(state_at_2, event_offset=2)
    service.snapshot_service.persist_snapshot(snapshot)
    
    # 4. ReplayService (Hybrid Replay)
    hybrid_state = service.load_replay(session_id)
    assert hybrid_state.metrics["reconstructed_from_snapshot"] is True
    assert hybrid_state.metrics["snapshot_offset"] == 2
    
    # 5. Compare states (excluding variable metrics)
    def clean_state(s):
        d = s.as_dict()
        d.pop("metrics")
        return d
        
    assert clean_state(full_state) == clean_state(hybrid_state)