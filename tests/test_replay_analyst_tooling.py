import pytest
import json
from pathlib import Path
from runtime.events.replay_bookmark import ReplayBookmark, BookmarkCategory
from runtime.events.bookmark_service import BookmarkService
from runtime.events.replay_annotation import ReplayAnnotation, AnnotationSeverity
from runtime.events.annotation_service import AnnotationService
from replay.verification.replay_search import ReplaySearch
from replay.verification.replay_compare import ReplayCompare
from runtime.state.replay_state import ReplayState

def test_bookmark_serialization(tmp_path):
    bookmark = ReplayBookmark(
        session_id="session-123",
        event_id="evt-1",
        event_index=5,
        media_time_ms=1500.0,
        label="Test Bookmark",
        category=BookmarkCategory.TRANSFER_POINT,
        note="Interesting point"
    )
    
    data = bookmark.to_dict()
    assert data["session_id"] == "session-123"
    assert data["category"] == "TRANSFER_POINT"
    
    restored = ReplayBookmark.from_dict(data)
    assert restored.label == "Test Bookmark"
    assert restored.category == BookmarkCategory.TRANSFER_POINT

def test_bookmark_service_append_only(tmp_path):
    service = BookmarkService(base_dir=tmp_path)
    b1 = ReplayBookmark(session_id="s1", event_id="e1", event_index=1, media_time_ms=100, label="L1", category=BookmarkCategory.OPERATOR_NOTE, note="N1")
    b2 = ReplayBookmark(session_id="s1", event_id="e2", event_index=2, media_time_ms=200, label="L2", category=BookmarkCategory.OPERATOR_NOTE, note="N2")
    
    service.add_bookmark(b1)
    service.add_bookmark(b2)
    
    bookmarks = service.get_bookmarks("s1")
    assert len(bookmarks) == 2
    assert bookmarks[0].label == "L1"
    assert bookmarks[1].label == "L2"

def test_annotation_revision_behavior(tmp_path):
    service = AnnotationService(base_dir=tmp_path)
    a1 = ReplayAnnotation(session_id="s1", event_id="e1", event_index=1, media_time_ms=100, type="T1", text="Original", severity=AnnotationSeverity.INFO)
    service.add_annotation(a1)
    
    # Revision
    a2 = ReplayAnnotation(session_id="s1", event_id="e1", event_index=1, media_time_ms=100, type="T1", text="Revised", severity=AnnotationSeverity.INFO, revision_of=a1.annotation_id)
    service.add_annotation(a2)
    
    annotations = service.get_annotations("s1")
    assert len(annotations) == 1
    assert annotations[0].text == "Revised"
    assert annotations[0].revision_of == a1.annotation_id

def test_replay_search_filters():
    state = ReplayState(session_id="s1")
    state.events = [
        {"type": "TRANSCRIPT_FINAL", "payload": {"text": "hello world", "confidence": 0.9}, "media_offset_ms": 1000},
        {"type": "DTMF_SENT", "payload": {"digits": "1"}, "media_offset_ms": 2000},
        {"type": "TRANSCRIPT_FINAL", "payload": {"text": "goodbye", "confidence": 0.5}, "media_offset_ms": 3000}
    ]
    
    # Search by query
    results = ReplaySearch.search_events(state, query="hello")
    assert len(results) == 1
    assert results[0]["event"]["payload"]["text"] == "hello world"
    
    # Search by DTMF
    results = ReplaySearch.search_events(state, dtmf_only=True)
    assert len(results) == 1
    assert results[0]["event"]["type"] == "DTMF_SENT"
    
    # Search by confidence
    results = ReplaySearch.search_events(state, min_confidence=0.8)
    assert len(results) == 1
    assert results[0]["event"]["payload"]["text"] == "hello world"

def test_replay_compare():
    left = ReplayState(session_id="left")
    left.active_path = ["root", "node1"]
    left.events = [{"type": "TRANSCRIPT_FINAL", "payload": {"text": "hi", "confidence": 1.0}, "media_offset_ms": 1000}]
    
    right = ReplayState(session_id="right")
    right.active_path = ["root", "node2"]
    right.events = [
        {"type": "TRANSCRIPT_FINAL", "payload": {"text": "hi", "confidence": 1.0}, "media_offset_ms": 1000},
        {"type": "TRANSCRIPT_FINAL", "payload": {"text": "there", "confidence": 0.8}, "media_offset_ms": 2000}
    ]
    
    summary = ReplayCompare.compare_sessions(left, right)
    assert summary["event_count_delta"] == 1
    assert summary["path_divergence_index"] == 1
    assert summary["confidence_delta_summary"]["left_avg"] == 1.0
    assert summary["confidence_delta_summary"]["right_avg"] == 0.9