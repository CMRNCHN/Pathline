import pytest
import shutil
import json
from pathlib import Path
from datetime import datetime
from ivr_assessor.events.replay_state import ReplayState
from ivr_assessor.events.snapshot_service import SnapshotService
from ivr_assessor.events.replay_snapshot import ReplaySnapshot

@pytest.fixture
def temp_snapshots_dir(tmp_path):
    return tmp_path / "snapshots"

@pytest.fixture
def snapshot_service(temp_snapshots_dir):
    return SnapshotService(snapshots_dir=temp_snapshots_dir)

def test_create_snapshot(snapshot_service):
    state = ReplayState(session_id="test_session")
    state.nodes = {"node1": {"id": "node1"}}
    state.call_status = "connected"
    
    snapshot = snapshot_service.create_snapshot(state, event_offset=10)
    
    assert snapshot.session_id == "test_session"
    assert snapshot.event_offset == 10
    assert snapshot.nodes == {"node1": {"id": "node1"}}
    assert snapshot.call_status == "connected"
    assert snapshot.snapshot_id.startswith("snap_10_")

def test_persist_and_load_snapshot(snapshot_service, temp_snapshots_dir):
    state = ReplayState(session_id="session_123")
    state.nodes = {"A": {"id": "A"}}
    
    snapshot = snapshot_service.create_snapshot(state, event_offset=5)
    file_path = snapshot_service.persist_snapshot(snapshot)
    
    assert file_path.exists()
    
    loaded = snapshot_service.load_snapshot("session_123", 5)
    assert loaded is not None
    assert loaded.session_id == "session_123"
    assert loaded.event_offset == 5
    assert loaded.nodes == {"A": {"id": "A"}}

def test_get_latest_snapshot(snapshot_service):
    session_id = "multi_snap"
    state = ReplayState(session_id=session_id)
    
    # Create 3 snapshots
    for offset in [10, 30, 20]:
        snap = snapshot_service.create_snapshot(state, event_offset=offset)
        snapshot_service.persist_snapshot(snap)
        
    latest = snapshot_service.get_latest_snapshot(session_id)
    assert latest is not None
    assert latest.event_offset == 30
