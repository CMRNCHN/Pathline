from runtime.state.replay_state import ReplayState, ReplayCursor
from replay.reducers.replay_reducer import apply_event
from runtime.events.event_types import EventType

def test_deterministic_media_offset_reconstruction():
    state = ReplayState(session_id="test_sync")
    
    events = [
        {
            "type": EventType.CALL_STARTED,
            "payload": {"call_sid": "CA_SYNC", "recording_url": "http://recording.url"},
            "meta": {"timestamp": 1000.0, "event_id": "e1"}
        },
        {
            "type": EventType.TRANSCRIPT_FINAL,
            "payload": {"text": "Hello", "speech_start_offset": 1.5},
            "meta": {"timestamp": 1002.0, "event_id": "e2"}
        },
        {
            "type": EventType.DTMF_SENT,
            "payload": {"digits": "1"},
            "meta": {"timestamp": 1005.5, "event_id": "e3"}
        }
    ]
    
    for e in events:
        state = apply_event(state, e)
    
    # Check anchor
    assert state.replay_anchor_timestamp == "1000.0"
    assert state.recording_reference == "http://recording.url"
    
    # Check decorated events in state
    decorated = state.events
    assert len(decorated) == 3
    
    # e1: CALL_ANCHOR
    assert decorated[0]["media_offset_ms"] == 0
    assert decorated[0]["alignment_source"] == "CALL_ANCHOR"
    
    # e2: STT_SPEECH_START (explicitly provided 1.5s)
    assert decorated[1]["media_offset_ms"] == 1500
    assert decorated[1]["alignment_source"] == "STT_SPEECH_START"
    
    # e3: CALL_ANCHOR (derived from 1005.5 - 1000.0 = 5.5s)
    assert decorated[2]["media_offset_ms"] == 5500
    assert decorated[2]["alignment_source"] == "CALL_ANCHOR"

def test_identical_replay_streams_produce_identical_offsets():
    events = [
        {"type": EventType.CALL_STARTED, "payload": {"call_sid": "CA1"}, "meta": {"timestamp": 1000.0}},
        {"type": EventType.DTMF_SENT, "payload": {"digits": "1"}, "meta": {"timestamp": 1002.5}}
    ]
    
    state1 = ReplayState(session_id="s1")
    for e in events:
        state1 = apply_event(state1, e)
        
    state2 = ReplayState(session_id="s1")
    for e in events:
        state2 = apply_event(state2, e)
        
    assert state1.events[1]["media_offset_ms"] == 2500
    assert state1.events[1]["media_offset_ms"] == state2.events[1]["media_offset_ms"]

def test_replay_cursor_serialization():
    cursor = ReplayCursor(
        event_index=5,
        event_id="evt_123",
        media_time_ms=5000,
        snapshot_anchor_offset=0
    )
    
    d = cursor.as_dict()
    assert d["event_index"] == 5
    assert d["event_id"] == "evt_123"
    assert d["media_time_ms"] == 5000
    
    # Test roundtrip (manual)
    cursor2 = ReplayCursor(**d)
    assert cursor == cursor2

def test_alignment_fallback_behavior():
    # Test case where CALL_STARTED is missing but other events have timestamps
    state = ReplayState(session_id="no_anchor")
    event = {
        "type": EventType.TRANSCRIPT_FINAL,
        "payload": {"text": "No anchor"},
        "meta": {"timestamp": 100.0}
    }
    
    state = apply_event(state, event)
    # Without anchor, it should NOT have media_offset_ms derived from CALL_ANCHOR
    # but might have ESTIMATED if we implemented that fallback fully.
    # Current implementation only sets alignment_source="ESTIMATED" for transcripts if media_offset_ms is still None.
    assert state.events[0]["alignment_source"] == "ESTIMATED"
    assert "media_offset_ms" not in state.events[0]

def test_malformed_missing_recording_reference_handling():
    state = ReplayState(session_id="malformed")
    # CALL_STARTED with NO payload
    event = {
        "type": EventType.CALL_STARTED,
        "payload": {},
        "meta": {"timestamp": "2024-01-01T00:00:00Z"}
    }
    state = apply_event(state, event)
    assert state.recording_reference is None
    assert state.replay_anchor_timestamp == "2024-01-01T00:00:00Z"
    
    # Even with malformed timestamp string, it should handle gracefully
    event2 = {
        "type": EventType.DTMF_SENT,
        "payload": {},
        "meta": {"timestamp": "not-a-timestamp"}
    }
    state = apply_event(state, event2)
    # Should not crash, and second event might not have offset
    assert "media_offset_ms" not in state.events[1]