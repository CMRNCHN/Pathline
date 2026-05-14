import pytest
from ivr_assessor.events.replay_state import ReplayState
from ivr_assessor.events.replay_reducer import apply_event
from ivr_assessor.events.event_types import EventType

def test_apply_call_started():
    state = ReplayState(session_id="test_session")
    event = {
        "type": EventType.CALL_STARTED,
        "payload": {"call_sid": "CA123"},
        "meta": {"timestamp": 1000.0}
    }
    new_state = apply_event(state, event)
    assert new_state.call_status == "started"
    assert new_state.call_sid == "CA123"
    assert new_state.created_at == "1000.0"
    assert new_state.updated_at == "1000.0"
    assert len(new_state.events) == 1

def test_apply_transcript():
    state = ReplayState(session_id="test_session")
    event = {
        "type": EventType.TRANSCRIPT_FINAL,
        "payload": {"text": "Hello world", "speaker": "system"},
        "meta": {"timestamp": 1001.0}
    }
    new_state = apply_event(state, event)
    assert len(new_state.transcripts) == 1
    assert new_state.transcripts[0]["text"] == "Hello world"
    assert new_state.transcripts[0]["speaker"] == "system"
    assert new_state.transcripts[0]["timestamp"] == 1001.0

def test_apply_node_discovered():
    state = ReplayState(session_id="test_session")
    event = {
        "type": EventType.NODE_DISCOVERED,
        "payload": {"id": "node_1", "label": "Welcome"},
        "meta": {"timestamp": 1002.0}
    }
    new_state = apply_event(state, event)
    assert "node_1" in new_state.nodes
    assert "node_1" in new_state.visited_nodes
    assert new_state.nodes["node_1"]["label"] == "Welcome"

def test_deterministic_reconstruction():
    events = [
        {"type": EventType.CALL_STARTED, "payload": {"call_sid": "CA1"}, "meta": {"timestamp": 1.0}},
        {"type": EventType.NODE_DISCOVERED, "payload": {"id": "n1"}, "meta": {"timestamp": 2.0}},
        {"type": EventType.TRANSCRIPT_FINAL, "payload": {"text": "Hi"}, "meta": {"timestamp": 3.0}},
        {"type": EventType.CALL_ENDED, "payload": {}, "meta": {"timestamp": 4.0}}
    ]
    
    state1 = ReplayState(session_id="s1")
    for e in events:
        state1 = apply_event(state1, e)
        
    state2 = ReplayState(session_id="s1")
    for e in events:
        state2 = apply_event(state2, e)
        
    assert state1.as_dict() == state2.as_dict()
    assert state1.call_status == "completed"
    assert len(state1.transcripts) == 1
    assert "n1" in state1.nodes
