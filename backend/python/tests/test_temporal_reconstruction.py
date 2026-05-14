import pytest
import json
from pathlib import Path
from ivr_assessor.events.replay_service import ReplayService
from ivr_assessor.events.event_types import EventType
from ivr_assessor.backend.ui.ui_state import EVENTS_DIR

@pytest.fixture
def temp_events_dir(tmp_path):
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    return events_dir

def test_partial_reconstruction(temp_events_dir):
    session_id = "test_partial"
    date_dir = temp_events_dir / "2026-05-13"
    date_dir.mkdir()
    session_file = date_dir / f"session_{session_id}.jsonl"
    
    events = [
        {"type": EventType.CALL_STARTED, "payload": {"call_sid": "sid1"}, "meta": {"timestamp": 1}},
        {"type": EventType.NODE_DISCOVERED, "payload": {"id": "n1"}, "meta": {"timestamp": 2}},
        {"type": EventType.TRANSCRIPT_FINAL, "payload": {"text": "hello"}, "meta": {"timestamp": 3}},
        {"type": EventType.NODE_DISCOVERED, "payload": {"id": "n2"}, "meta": {"timestamp": 4}},
    ]
    
    with open(session_file, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
            
    service = ReplayService(events_dir=temp_events_dir)
    
    # Reconstruct at offset 2 (Started + n1)
    state_2 = service.load_replay(session_id, offset=2)
    assert state_2.call_sid == "sid1"
    assert "n1" in state_2.nodes
    assert "n2" not in state_2.nodes
    assert len(state_2.transcripts) == 0
    
    # Reconstruct at offset 3 (Started + n1 + hello)
    state_3 = service.load_replay(session_id, offset=3)
    assert len(state_3.transcripts) == 1
    assert state_3.transcripts[0]["text"] == "hello"
    assert "n2" not in state_3.nodes
    
    # Reconstruct at full offset
    state_4 = service.load_replay(session_id)
    assert "n2" in state_4.nodes
    assert len(state_4.transcripts) == 1
