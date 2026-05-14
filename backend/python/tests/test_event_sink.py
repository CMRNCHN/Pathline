import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from ivr_assessor.events.event_sink import EventSink
from ivr_assessor.events.event_models import OperationalEvent, EventMetadata
from ivr_assessor.events.event_types import EventType

def test_event_sink_persists_events_to_jsonl():
    temp_dir = Path(tempfile.mkdtemp())
    sink = EventSink(base_dir=temp_dir)
    
    event = OperationalEvent(
        type=EventType.TRANSCRIPT_FINAL,
        payload={"text": "Hello world"},
        meta=EventMetadata(
            session_id="test-session-123",
            source_component="test-component",
            timestamp=1700000000.0
        )
    )
    
    sink.persist(event)
    
    # Path should be temp_dir / 2023-11-14 / session_test-session-123.jsonl
    # 1700000000.0 is 2023-11-14T22:13:20Z
    expected_path = temp_dir / "2023-11-14" / "session_test-session-123.jsonl"
    
    assert expected_path.exists()
    
    with open(expected_path, "r") as f:
        data = json.loads(f.read())
        assert data["type"] == "TRANSCRIPT_FINAL"
        assert data["session_id"] == "test-session-123"
        assert data["payload"]["text"] == "Hello world"
    
    shutil.rmtree(temp_dir)

def test_event_sink_append_only():
    temp_dir = Path(tempfile.mkdtemp())
    sink = EventSink(base_dir=temp_dir)
    
    meta = EventMetadata(session_id="session-1", timestamp=1700000000.0)
    event1 = OperationalEvent(type=EventType.CALL_STARTED, payload={}, meta=meta)
    event2 = OperationalEvent(type=EventType.TRANSCRIPT_FINAL, payload={"text": "hi"}, meta=meta)
    
    sink.persist(event1)
    sink.persist(event2)
    
    expected_path = temp_dir / "2023-11-14" / "session_session-1.jsonl"
    with open(expected_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        assert "CALL_STARTED" in lines[0]
        assert "TRANSCRIPT_FINAL" in lines[1]
    
    shutil.rmtree(temp_dir)

def test_event_sink_unknown_session():
    temp_dir = Path(tempfile.mkdtemp())
    sink = EventSink(base_dir=temp_dir)
    
    event = OperationalEvent(
        type=EventType.ERROR_RAISED,
        payload={"msg": "test"},
        meta=EventMetadata(session_id=None, timestamp=1700000000.0)
    )
    
    sink.persist(event)
    
    expected_path = temp_dir / "2023-11-14" / "session_unknown_session.jsonl"
    assert expected_path.exists()
    
    shutil.rmtree(temp_dir)

def test_event_sink_metrics():
    temp_dir = Path(tempfile.mkdtemp())
    sink = EventSink(base_dir=temp_dir)
    
    event = OperationalEvent(
        type=EventType.ERROR_RAISED,
        payload={},
        meta=EventMetadata(session_id="s1", timestamp=1700000000.0)
    )
    
    sink.persist(event)
    metrics = sink.metrics()
    
    assert metrics["persisted_event_count"] == 1
    assert "session_s1.jsonl" in metrics["current_event_log_path"]
    assert metrics["sink_errors"] == 0
    
    shutil.rmtree(temp_dir)
