import pytest
from pathlib import Path
from runtime.state.replay_state import ReplayState
from replay.reducers.replay_reducer import apply_event
from replay.snapshots.snapshot_service import SnapshotService
from replay.timelines.replay_service import ReplayService
from infrastructure.config.paths import EVENTS_DIR, SNAPSHOTS_DIR

@pytest.fixture
def sample_events():
    return [
        {"ts": 1000, "type": "CALL_STARTED", "session_id": "test_pure", "payload": {"call_sid": "sid_1"}},
        {"ts": 2000, "type": "TRANSCRIPT_FINAL", "session_id": "test_pure", "payload": {"text": "hello", "confidence": 0.9}},
        {"ts": 3000, "type": "NODE_ENTERED", "session_id": "test_pure", "payload": {"node_id": "welcome"}},
        {"ts": 4000, "type": "TRANSCRIPT_FINAL", "session_id": "test_pure", "payload": {"text": "support", "confidence": 0.8}},
        {"ts": 5000, "type": "NODE_ENTERED", "session_id": "test_pure", "payload": {"node_id": "support_menu"}},
        {"ts": 6000, "type": "CALL_COMPLETED", "session_id": "test_pure", "payload": {}}
    ]

def test_replay_determinism_and_snapshot_equivalence(tmp_path, sample_events):
    """
    Verifies that Replay reconstruction is stable regardless of snapshot boundary.
    1. Reconstruct state by applying all events directly.
    2. Create a snapshot at the middle of the stream.
    3. Reconstruct state using the snapshot + remaining events.
    4. Verify both states are equivalent.
    """
    # Setup directories
    events_dir = tmp_path / "events" / "2026-05-18"
    events_dir.mkdir(parents=True)
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir(parents=True)
    
    session_id = "test_pure"
    event_file = events_dir / f"session_{session_id}.jsonl"
    
    import json
    with open(event_file, "w") as f:
        for e in sample_events:
            f.write(json.dumps(e) + "\n")
            
    # 1. Full reconstruction from scratch
    state_full = ReplayState(session_id=session_id)
    for e in sample_events:
        state_full = apply_event(state_full, e)
        
    # 2. Create a snapshot at index 3 (offset 3)
    state_mid = ReplayState(session_id=session_id)
    for e in sample_events[:3]:
        state_mid = apply_event(state_mid, e)
        
    snap_service = SnapshotService(snapshots_dir=snapshots_dir)
    snapshot = snap_service.create_snapshot(state_mid, event_offset=3)
    snap_service.persist_snapshot(snapshot)
    
    # 3. Reconstruct using ReplayService (which should use the snapshot)
    replay_service = ReplayService(events_dir=tmp_path / "events")
    # Inject our custom snapshot service to use tmp_path
    replay_service.snapshot_service = snap_service
    
    state_reconstructed = replay_service.load_replay(session_id)
    
    # 4. Assertions
    assert state_reconstructed.metrics["reconstructed_from_snapshot"] is True
    assert state_reconstructed.metrics["snapshot_offset"] == 3
    
    # Compare core data structures
    assert state_reconstructed.session_id == state_full.session_id
    assert state_reconstructed.nodes == state_full.nodes
    assert state_reconstructed.edges == state_full.edges
    assert state_reconstructed.transcripts == state_full.transcripts
    assert state_reconstructed.active_path == state_full.active_path
    assert state_reconstructed.visited_nodes == state_full.visited_nodes
    assert len(state_reconstructed.events) == len(state_full.events)
    
    # Verify temporal ordering in events
    offsets = [e.get("media_offset_ms") for e in state_reconstructed.events if e.get("media_offset_ms") is not None]
    assert offsets == sorted(offsets), "Events must maintain temporal ordering"

def test_seek_equivalence(tmp_path, sample_events):
    """
    Verifies that seeking to an offset produces the same state as manual application to that offset.
    """
    events_dir = tmp_path / "events" / "2026-05-18"
    events_dir.mkdir(parents=True)
    session_id = "test_seek"
    event_file = events_dir / f"session_{session_id}.jsonl"
    
    import json
    with open(event_file, "w") as f:
        for e in sample_events:
            f.write(json.dumps(e) + "\n")
            
    replay_service = ReplayService(events_dir=tmp_path / "events")
    
    # Target offset 4
    state_seek = replay_service.load_replay(session_id, offset=4)
    
    state_manual = ReplayState(session_id=session_id)
    for e in sample_events[:4]:
        state_manual = apply_event(state_manual, e)
        
    assert state_seek.nodes == state_manual.nodes
    assert state_seek.active_path == state_manual.active_path
    assert len(state_seek.events) == 4
