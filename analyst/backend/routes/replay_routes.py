"""Replay API route handlers."""
from __future__ import annotations
from typing import Any
from replay.timelines.replay_service import ReplayService
from replay.media_sync.waveform_metadata import WaveformService
from runtime.state.replay_state import ReplayCursor
from replay.media_sync.media_replay_service import MediaReplayService
from runtime.events.bookmark_service import bookmark_service as _bookmark_service
from runtime.events.annotation_service import annotation_service as _annotation_service
from runtime.events.replay_bookmark import ReplayBookmark, BookmarkCategory
from runtime.events.replay_annotation import ReplayAnnotation, AnnotationSeverity
from replay.verification.replay_search import ReplaySearch
from replay.verification.replay_compare import ReplayCompare

_replay_service = ReplayService()
_waveform_service = WaveformService()
_media_replay_service = MediaReplayService(waveform_service=_waveform_service)


class ReplayError(Exception):
    """Base exception for replay errors with HTTP semantics."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _validate_replay_session(session_id: str, offset: int | None = None) -> None:
    """Validate that a replay session exists and offset is within bounds."""
    session_file = _replay_service._find_session_file(session_id)
    if not session_file:
        raise ReplayError(f"Replay session {session_id} not found", status_code=404)

    events = _replay_service.get_raw_events(session_id)
    total_events = len(events)

    if offset is not None:
        if offset < 0 or offset > total_events:
            raise ReplayError(
                f"Event offset {offset} out of range [0, {total_events}]",
                status_code=400
            )


def get_replays() -> list[dict[str, Any]]:
    """Return a list of available replay sessions."""
    return _replay_service.list_replays()

def get_replay(session_id: str, offset: int | None = None) -> dict[str, Any]:
    """Return reconstructed replay state for a session."""
    _validate_replay_session(session_id, offset)
    state = _replay_service.load_replay(session_id, offset=offset)
    if not state:
        raise ReplayError(f"Failed to load replay state for {session_id}", status_code=400)
    return state.as_dict()

def get_replay_timeline(session_id: str) -> dict[str, Any]:
    """Return timeline summary for a session."""
    _validate_replay_session(session_id)
    events = _replay_service.get_raw_events(session_id)
    if not events and not _replay_service._find_session_file(session_id):
        raise ReplayError(f"Replay session {session_id} not found", status_code=404)
    
    # We might want to include snapshot offsets here for the frontend
    session_dir = _replay_service.snapshot_service._find_session_dir(session_id)
    snapshots = []
    if session_dir:
        for path in session_dir.glob("snapshot_*.json"):
            try:
                snapshots.append(int(path.stem.split("_")[1]))
            except (IndexError, ValueError):
                continue

    return {
        "session_id": session_id,
        "total_events": len(events),
        "snapshots": sorted(snapshots),
        "event_types": sorted(list(set(e.get("type") for e in events if e.get("type"))))
    }

def get_replay_diff(session_id: str, from_offset: int, to_offset: int) -> dict[str, Any]:
    """Return operational delta between two states."""
    from ...events.replay_diff import diff_states

    _validate_replay_session(session_id, from_offset)
    _validate_replay_session(session_id, to_offset)

    state_before = None
    if from_offset > 0:
        state_before = _replay_service.load_replay(session_id, offset=from_offset)
        if not state_before:
            raise ReplayError(f"Failed to load replay state at offset {from_offset}", status_code=400)

    state_after = _replay_service.load_replay(session_id, offset=to_offset)
    if not state_after:
        raise ReplayError(f"Failed to load replay state at offset {to_offset}", status_code=400)

    return diff_states(state_before, state_after)

def get_replay_events(session_id: str) -> list[dict[str, Any]]:
    """Return the raw event stream for a session."""
    _validate_replay_session(session_id)
    events = _replay_service.get_raw_events(session_id)
    if not events:
        # Check if it actually exists but has no events
        if not _replay_service._find_session_file(session_id):
            raise ReplayError(f"Replay session {session_id} not found", status_code=404)
    return events

def get_replay_media_metadata(session_id: str) -> dict[str, Any]:
    """Return media-specific metadata for a session."""
    _validate_replay_session(session_id)
    state = _replay_service.load_replay(session_id)
    if not state:
        raise ReplayError(f"Replay session {session_id} not found", status_code=404)
    
    return {
        "session_id": session_id,
        "recording_reference": state.recording_reference,
        "media_duration_ms": state.media_duration_ms,
        "replay_anchor_timestamp": state.replay_anchor_timestamp,
        "waveform_reference": state.waveform_reference
    }

def get_replay_cursor(session_id: str, offset: int) -> dict[str, Any]:
    """Return cursor position for a given event offset."""
    _validate_replay_session(session_id, offset)
    state = _replay_service.load_replay(session_id, offset=offset)
    if not state:
        raise ReplayError(f"Replay session {session_id} not found", status_code=404)
    
    events = state.events
    if not events:
        return ReplayCursor(event_index=0, event_id="none", media_time_ms=0).as_dict()
    
    last_event = events[-1]
    return ReplayCursor(
        event_index=len(events) - 1,
        event_id=last_event.get("meta", {}).get("event_id", "unknown"),
        media_time_ms=last_event.get("media_offset_ms", 0),
        snapshot_anchor_offset=state.metrics.get("snapshot_offset", 0)
    ).as_dict()

def get_waveform_metadata(session_id: str) -> dict[str, Any]:
    """Return waveform peak/RMS metadata. Returns empty object if recording missing."""
    try:
        waveform = _waveform_service.get_waveform_for_session(session_id)
        if not waveform:
            return {"peaks": [], "rms_buckets": [], "bucket_size_ms": 100, "duration_ms": 0}
        return waveform.as_dict()
    except Exception:
        return {"peaks": [], "rms_buckets": [], "bucket_size_ms": 100, "duration_ms": 0}

def get_alignment_lookup(session_id: str) -> list[dict[str, Any]]:
    """Return alignment metadata for all events in a session."""
    _validate_replay_session(session_id)
    state = _replay_service.load_replay(session_id)
    if not state:
        raise ReplayError(f"Replay session {session_id} not found", status_code=404)
    
    return [
        {
            "event_id": e.get("meta", {}).get("event_id"),
            "type": e.get("type"),
            "media_offset_ms": e.get("media_offset_ms"),
            "alignment_source": e.get("alignment_source")
        }
        for e in state.events
    ]

def seek_replay(session_id: str, media_time_ms: int) -> dict[str, Any]:
    """Return replay state and cursor at a specific media time."""
    cursor = _replay_service.get_cursor_for_time(session_id, media_time_ms)
    if not cursor:
        raise FileNotFoundError(f"No events found for {session_id} at {media_time_ms}ms")
    
    # We also return the state at that event offset
    state = _replay_service.load_replay(session_id, offset=cursor["event_index"] + 1)
    
    return {
        "cursor": cursor,
        "state": state.as_dict() if state else None
    }

def get_event_at_index(session_id: str, index: int) -> dict[str, Any]:
    """Return event at specific index with its media alignment."""
    state = _replay_service.load_replay(session_id, offset=index + 1)
    if not state or not state.events:
        raise FileNotFoundError(f"Event {index} not found for session {session_id}")
    
    event = state.events[-1]
    return {
        "index": index,
        "event": event,
        "media_offset_ms": event.get("media_offset_ms"),
        "total_events": state.metrics.get("total_event_count", 0)
    }

def stream_media(session_id: str) -> Any:
    """Stream the audio recording for a session."""
    recording_path = _media_replay_service.resolve_recording_path(session_id)
    if not recording_path or not recording_path.exists():
        raise FileNotFoundError(f"Recording for session {session_id} not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(path=recording_path, media_type="audio/wav")

# Bookmark APIs
def get_replay_bookmarks(session_id: str) -> list[dict[str, Any]]:
    """Return all bookmarks for a session."""
    bookmarks = _bookmark_service.get_bookmarks(session_id)
    return [b.to_dict() for b in bookmarks]

def create_replay_bookmark(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new bookmark for a session."""
    bookmark = ReplayBookmark(
        session_id=session_id,
        event_id=payload["event_id"],
        event_index=payload["event_index"],
        media_time_ms=payload["media_time_ms"],
        label=payload["label"],
        category=BookmarkCategory(payload["category"]),
        note=payload.get("note", ""),
        source=payload.get("source", "operator")
    )
    _bookmark_service.add_bookmark(bookmark)
    return bookmark.to_dict()

# Annotation APIs
def get_replay_annotations(session_id: str) -> list[dict[str, Any]]:
    """Return all annotations for a session."""
    annotations = _annotation_service.get_annotations(session_id)
    return [a.to_dict() for a in annotations]

def create_replay_annotation(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new annotation for a session."""
    annotation = ReplayAnnotation(
        session_id=session_id,
        event_id=payload["event_id"],
        event_index=payload["event_index"],
        media_time_ms=payload["media_time_ms"],
        type=payload["type"],
        text=payload["text"],
        severity=AnnotationSeverity(payload["severity"]),
        revision_of=payload.get("revision_of")
    )
    _annotation_service.add_annotation(annotation)
    return annotation.to_dict()

# Search API
def search_replay(session_id: str, query_params: dict[str, Any]) -> list[dict[str, Any]]:
    """Search events in a session."""
    state = _replay_service.load_replay(session_id)
    if not state:
        raise FileNotFoundError(f"Replay session {session_id} not found")
    
    results = ReplaySearch.search_events(
        state,
        event_types=query_params.get("event_types"),
        query=query_params.get("query"),
        dtmf_only=query_params.get("dtmf_only", "false").lower() == "true",
        min_confidence=float(query_params.get("min_confidence")) if query_params.get("min_confidence") else None,
        media_time_range=query_params.get("media_time_range"),
        event_index_range=query_params.get("event_index_range")
    )
    return ReplaySearch.format_results(results)

# Compare API
def compare_replays(left_session_id: str, right_session_id: str) -> dict[str, Any]:
    """Compare two replay sessions."""
    left_state = _replay_service.load_replay(left_session_id)
    if not left_state:
        raise FileNotFoundError(f"Replay session {left_session_id} not found")
    
    right_state = _replay_service.load_replay(right_session_id)
    if not right_state:
        raise FileNotFoundError(f"Replay session {right_session_id} not found")
        
    return ReplayCompare.compare_sessions(left_state, right_state)