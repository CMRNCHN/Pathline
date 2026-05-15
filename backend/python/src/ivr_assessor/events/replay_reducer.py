import logging
from datetime import datetime
from typing import Any, Dict, Optional
from .event_types import EventType
from .replay_state import ReplayState

logger = logging.getLogger(__name__)

def parse_timestamp(ts: Any) -> Optional[float]:
    """Helper to parse various timestamp formats to float seconds."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        try:
            # Try ISO format
            return datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
        except ValueError:
            try:
                # Try float string
                return float(ts)
            except ValueError:
                pass
    return None

def apply_event(state: ReplayState, event: Dict[str, Any]) -> ReplayState:
    """
    Pure deterministic reducer for ReplayState.
    Takes a state and an event (as dict), returns the updated state.
    """
    event_type = event.get("type")
    payload = event.get("payload", {})
    meta = event.get("meta", {})
    timestamp_raw = meta.get("timestamp") or event.get("ts")
    timestamp = parse_timestamp(timestamp_raw)

    # Update updated_at for every valid event (keep as raw for consistency)
    if timestamp_raw:
        state.updated_at = str(timestamp_raw)

    # Media offset derivation
    media_offset_ms = None
    relative_time_ms = None
    alignment_source = None

    anchor_ts = parse_timestamp(state.replay_anchor_timestamp)
    current_ts = timestamp

    if event_type == EventType.CALL_STARTED:
        state.call_status = "started"
        state.call_sid = payload.get("call_sid")
        state.recording_reference = payload.get("recording_url") or payload.get("call_sid")
        
        if not state.created_at:
            state.created_at = str(timestamp_raw)
        
        # Establish T=0 anchor
        if current_ts is not None:
            state.replay_anchor_timestamp = str(timestamp_raw)
            anchor_ts = current_ts
            # We don't return here, we fall through to ensure media_offset_ms is set below

    if anchor_ts is not None and current_ts is not None:
        # Derive media offset from anchor
        media_offset_ms = int((current_ts - anchor_ts) * 1000)
        relative_time_ms = media_offset_ms
        if not alignment_source:
            alignment_source = "CALL_ANCHOR"

    # Transcript-specific alignment
    if event_type == EventType.TRANSCRIPT_FINAL:
        speech_start = payload.get("speech_start_offset")
        if speech_start is not None:
            media_offset_ms = int(speech_start * 1000)
            alignment_source = "STT_SPEECH_START"
        elif media_offset_ms is None:
            # Fallback to estimated if no anchor but we have order
            alignment_source = "ESTIMATED"

    # Decorate event with alignment metadata (for in-memory state)
    decorated_event = event.copy()
    if media_offset_ms is not None:
        decorated_event["media_offset_ms"] = media_offset_ms
    if relative_time_ms is not None:
        decorated_event["relative_time_ms"] = relative_time_ms
    if alignment_source:
        decorated_event["alignment_source"] = alignment_source

    state.events.append(decorated_event)

    try:
        if event_type == EventType.CALL_CONNECTED:
            state.call_status = "connected"

        elif event_type == EventType.CALL_ENDED or event_type == EventType.CALL_COMPLETED:
            state.call_status = "completed"

        elif event_type == EventType.STATE_DISCOVERED or event_type == EventType.NODE_DISCOVERED:
            node_id = payload.get("id") or payload.get("node_id")
            if node_id:
                state.nodes[node_id] = payload
                if node_id not in state.visited_nodes:
                    state.visited_nodes.append(node_id)

        elif event_type == EventType.EDGE_DISCOVERED:
            state.edges.append(payload)

        elif event_type == EventType.TRANSCRIPT_FINAL:
            state.transcripts.append({
                "text": payload.get("text"),
                "speaker": payload.get("speaker", "system"),
                "timestamp": timestamp
            })

        elif event_type == EventType.DTMF_SENT:
            digits = payload.get("digits")
            if digits:
                state.dtmf_history.append(digits)

        elif event_type == EventType.PATH_ADVANCED:
            node_id = payload.get("node_id")
            if node_id:
                state.active_path.append(node_id)
                if node_id not in state.visited_nodes:
                    state.visited_nodes.append(node_id)

        elif event_type == EventType.GRAPH_UPDATED:
            # Full graph replacement or partial update
            nodes = payload.get("nodes")
            edges = payload.get("edges")
            if nodes:
                state.nodes.update(nodes)
            if edges:
                state.edges = edges

        elif event_type == EventType.ERROR_RAISED:
            state.metrics["last_error"] = payload.get("message")

    except Exception as e:
        logger.warning(f"Error reducing event {event_type}: {e}")

    return state
