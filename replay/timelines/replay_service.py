from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Optional
from replay.timelines.replay_loader import ReplayLoader
from runtime.state.replay_state import ReplayState
from replay.reducers.replay_reducer import apply_event
from replay.snapshots.snapshot_service import SnapshotService
from replay.snapshots.snapshot_validator import SnapshotValidator
from infrastructure.config.paths import EVENTS_DIR

logger = logging.getLogger(__name__)

class ReplayService:
    """
    Handles loading session events and reconstructing deterministic ReplayState.
    """
    def __init__(self, events_dir: Path = EVENTS_DIR):
        self.events_dir = events_dir
        self.snapshot_service = SnapshotService()

    def list_replays(self) -> list[dict[str, Any]]:
        """List all available replays by scanning the events directory."""
        replays = []
        if not self.events_dir.exists():
            return replays

        # Events are stored in YYYY-MM-DD/session_<id>.jsonl
        for date_dir in sorted(self.events_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                for session_file in sorted(date_dir.glob("session_*.jsonl"), reverse=True):
                    session_id = session_file.stem.replace("session_", "")
                    
                    # For indexing, we might want minimal info without loading all events
                    # But Slice 4 asks for event_count, created_at, updated_at
                    loader = ReplayLoader(session_file)
                    events = loader.load_events()
                    
                    if events:
                        first_event = events[0]
                        last_event = events[-1]
                        replays.append({
                            "session_id": session_id,
                            "event_count": len(events),
                            "created_at": first_event.get("meta", {}).get("timestamp") or first_event.get("ts"),
                            "updated_at": last_event.get("meta", {}).get("timestamp") or last_event.get("ts"),
                            "date": date_dir.name
                        })
        return replays

    def load_replay(self, session_id: str, offset: Optional[int] = None) -> Optional[ReplayState]:
        """Reconstruct ReplayState for a given session_id using hybrid loading."""
        session_file = self._find_session_file(session_id)
        if not session_file:
            logger.error(f"Session file not found for {session_id}")
            return None

        loader = ReplayLoader(session_file)
        events = loader.get_timeline()
        total_events = len(events)

        if offset is not None:
            if offset < 0:
                offset = 0
            elif offset > total_events:
                offset = total_events
            events_to_apply = events[:offset]
        else:
            offset = total_events
            events_to_apply = events

        # 1. Attempt to load latest snapshot that is within our offset
        snapshot = self._get_best_snapshot(session_id, offset)

        reconstructed_from_snapshot = False
        snapshot_offset = 0

        if snapshot and SnapshotValidator.is_valid(snapshot):
            state = ReplayState(
                session_id=snapshot.session_id,
                call_sid=snapshot.call_sid,
                created_at=snapshot.created_at,
                nodes=snapshot.nodes.copy(),
                edges=snapshot.edges.copy(),
                transcripts=snapshot.transcripts.copy(),
                metrics=snapshot.metrics.copy(),
                visited_nodes=snapshot.visited_nodes.copy(),
                dtmf_history=snapshot.dtmf_history.copy(),
                active_path=snapshot.active_path.copy(),
                call_status=snapshot.call_status,
                events=snapshot.events.copy(),
                updated_at=snapshot.updated_at,
                recording_reference=getattr(snapshot, "recording_reference", None),
                media_duration_ms=getattr(snapshot, "media_duration_ms", None),
                replay_anchor_timestamp=getattr(snapshot, "replay_anchor_timestamp", None),
                waveform_reference=getattr(snapshot, "waveform_reference", None)
            )
            snapshot_offset = snapshot.event_offset
            # Remaining events are those after the snapshot_offset up to our target offset
            remaining_events = events[snapshot_offset:offset]
            reconstructed_from_snapshot = True
        else:
            state = ReplayState(session_id=session_id)
            remaining_events = events_to_apply

        # 2. Apply remaining events incrementally
        for event in remaining_events:
            state = apply_event(state, event)

        # 3. Attach reconstruction metadata
        state.metrics["reconstructed_from_snapshot"] = reconstructed_from_snapshot
        state.metrics["snapshot_offset"] = snapshot_offset
        state.metrics["target_offset"] = offset
        state.metrics["total_event_count"] = total_events

        return state

    def _get_best_snapshot(self, session_id: str, max_offset: int) -> Optional[Any]:
        """Find the snapshot with the largest event_offset <= max_offset."""
        session_dir = self.snapshot_service._find_session_dir(session_id)
        if not session_dir:
            return None

        snapshots = list(session_dir.glob("snapshot_*.json"))
        if not snapshots:
            return None

        best_snapshot_path = None
        best_offset = -1

        for path in snapshots:
            try:
                offset = int(path.stem.split("_")[1])
                if offset <= max_offset and offset > best_offset:
                    best_offset = offset
                    best_snapshot_path = path
            except (IndexError, ValueError):
                continue

        if not best_snapshot_path:
            return None

        try:
            with open(best_snapshot_path, "r", encoding="utf-8") as f:
                import json
                from replay.snapshots.replay_snapshot import ReplaySnapshot
                data = json.load(f)
                return ReplaySnapshot.from_dict(data)
        except Exception:
            logger.exception(f"Failed to load snapshot from {best_snapshot_path}")
            return None

    def get_raw_events(self, session_id: str) -> list[dict[str, Any]]:
        """Return ordered raw event stream for a session."""
        session_file = self._find_session_file(session_id)
        if not session_file:
            return []
        
        loader = ReplayLoader(session_file)
        return loader.get_timeline()

    def _find_session_file(self, session_id: str) -> Optional[Path]:
        """Locate the .jsonl file for a session_id by searching all date directories."""
        if not self.events_dir.exists():
            return None
            
        for date_dir in self.events_dir.iterdir():
            if date_dir.is_dir():
                potential_file = date_dir / f"session_{session_id}.jsonl"
                if potential_file.exists():
                    return potential_file
        return None

    def get_nearest_event_for_timestamp(self, session_id: str, media_time_ms: int) -> dict[str, Any] | None:
        """
        Returns the event that is active at the given media time.
        Uses deterministic media_offset_ms if available in the event stream.
        """
        # We need a fully reconstructed state to see media offsets, 
        # or we can look at the timeline if events were decorated.
        # Loader's get_timeline() returns raw events.
        # ReplayState contains decorated events after apply_event.
        
        state = self.load_replay(session_id)
        if not state or not state.events:
            return None
            
        # Find the last event whose media_offset_ms <= media_time_ms
        best_event = None
        best_index = -1
        
        for i, event in enumerate(state.events):
            offset = event.get("media_offset_ms")
            if offset is not None and offset <= media_time_ms:
                best_event = event
                best_index = i
            elif offset is not None and offset > media_time_ms:
                break
                
        if best_event:
            return {
                "event": best_event,
                "index": best_index
            }
        return None

    def get_cursor_for_time(self, session_id: str, media_time_ms: int) -> dict[str, Any] | None:
        """
        Returns a ReplayCursor for a specific media time.
        """
        nearest = self.get_nearest_event_for_timestamp(session_id, media_time_ms)
        if not nearest:
            return None
            
        from runtime.state.replay_state import ReplayCursor
        event = nearest["event"]
        index = nearest["index"]
        
        cursor = ReplayCursor(
            event_index=index,
            event_id=event.get("event_id", f"idx_{index}"),
            media_time_ms=media_time_ms,
            active_event_index=index
        )
        return cursor.as_dict()
