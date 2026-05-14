"""Replay API route handlers."""
from __future__ import annotations
from typing import Any
from ...events.replay_service import ReplayService
from ...events.waveform_metadata import WaveformService
from ...events.replay_state import ReplayCursor

_replay_service = ReplayService()
_waveform_service = WaveformService()

def get_replays() -> list[dict[str, Any]]:
    """Return a list of available replay sessions."""
    return _replay_service.list_replays()

def get_replay(session_id: str, offset: int | None = None) -> dict[str, Any]:
    """Return reconstructed replay state for a session."""
    state = _replay_service.load_replay(session_id, offset=offset)
    if not state:
        raise FileNotFoundError(f"Replay session {session_id} not found")
    return state.as_dict()

def get_replay_timeline(session_id: str) -> dict[str, Any]:
    """Return timeline summary for a session."""
    events = _replay_service.get_raw_events(session_id)
    if not events and not _replay_service._find_session_file(session_id):
        raise FileNotFoundError(f"Replay session {session_id} not found")
    
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
    
    state_before = None
    if from_offset > 0:
        state_before = _replay_service.load_replay(session_id, offset=from_offset)
        if not state_before:
            raise FileNotFoundError(f"Replay session {session_id} (offset {from_offset}) not found")
            
    state_after = _replay_service.load_replay(session_id, offset=to_offset)
    if not state_after:
        raise FileNotFoundError(f"Replay session {session_id} (offset {to_offset}) not found")
        
    return diff_states(state_before, state_after)

def get_replay_events(session_id: str) -> list[dict[str, Any]]:
    """Return the raw event stream for a session."""
    events = _replay_service.get_raw_events(session_id)
    if not events:
        # Check if it actually exists but has no events
        if not _replay_service._find_session_file(session_id):
            raise FileNotFoundError(f"Replay session {session_id} not found")
    return events

def get_replay_media_metadata(session_id: str) -> dict[str, Any]:
    """Return media-specific metadata for a session."""
    state = _replay_service.load_replay(session_id)
    if not state:
        raise FileNotFoundError(f"Replay session {session_id} not found")
    
    return {
        "session_id": session_id,
        "recording_reference": state.recording_reference,
        "media_duration_ms": state.media_duration_ms,
        "replay_anchor_timestamp": state.replay_anchor_timestamp,
        "waveform_reference": state.waveform_reference
    }

def get_replay_cursor(session_id: str, offset: int) -> dict[str, Any]:
    """Return cursor position for a given event offset."""
    state = _replay_service.load_replay(session_id, offset=offset)
    if not state:
        raise FileNotFoundError(f"Replay session {session_id} not found")
    
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
    """Return waveform peak/RMS metadata."""
    waveform = _waveform_service.get_waveform_for_session(session_id)
    if not waveform:
        return {}
    return waveform.as_dict()

def get_alignment_lookup(session_id: str) -> list[dict[str, Any]]:
    """Return alignment metadata for all events in a session."""
    state = _replay_service.load_replay(session_id)
    if not state:
        raise FileNotFoundError(f"Replay session {session_id} not found")
    
    return [
        {
            "event_id": e.get("meta", {}).get("event_id"),
            "type": e.get("type"),
            "media_offset_ms": e.get("media_offset_ms"),
            "alignment_source": e.get("alignment_source")
        }
        for e in state.events
    ]
