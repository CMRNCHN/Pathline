import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

from runtime.events.event_bus import bus
from runtime.events.event_models import OperationalEvent
from runtime.events.event_types import EventType
from runtime.state.replay_state import ReplayState
from replay.reducers.replay_reducer import apply_event
from replay.snapshots.snapshot_service import SnapshotService
from analyst.backend.ui.ui_state import EVENTS_DIR, SNAPSHOT_INTERVAL

logger = logging.getLogger(__name__)

class EventSink:
    """
    Persists OperationalEvents to append-only JSONL files.
    """
    def __init__(self, base_dir: Path = EVENTS_DIR):
        self.base_dir = base_dir
        self._lock = threading.Lock()
        self._persisted_count = 0
        self._errors = 0
        self._current_path: Optional[Path] = None
        self._active_files: Dict[str, Path] = {}
        self._states: Dict[str, ReplayState] = {}
        self._offsets: Dict[str, int] = {}
        self._snapshot_service = SnapshotService()

    def start(self):
        """Subscribe to the event bus and start persisting events."""
        bus.subscribe_all(self.on_event)
        logger.info("EventSink started and subscribed to EventBus")

    def stop(self):
        """Unsubscribe from the event bus."""
        # Note: EventBus doesn't have an unsubscribe_all yet, but we can just stop processing.
        pass

    def on_event(self, event: OperationalEvent):
        """Handle an incoming event from the bus."""
        try:
            self.persist(event)
        except Exception:
            self._errors += 1
            logger.exception("Failed to persist event")

    def persist(self, event: OperationalEvent):
        """Write the event to the appropriate JSONL file."""
        session_id = event.meta.session_id or "unknown_session"
        
        # Determine the file path
        date_str = datetime.fromtimestamp(event.meta.timestamp).strftime("%Y-%m-%d")
        dir_path = self.base_dir / date_str
        file_path = dir_path / f"session_{session_id}.jsonl"

        with self._lock:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
            
            event_data = {
                "ts": event.meta.timestamp,
                "event_id": event.meta.event_id,
                "type": event.type,
                "session_id": event.meta.session_id,
                "state_id": event.meta.state_id,
                "path_id": event.meta.path_id,
                "source_component": event.meta.source_component,
                "payload": event.payload
            }
            
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_data) + "\n")
            
            self._persisted_count += 1
            self._current_path = file_path
            self._active_files[session_id] = file_path

            # Increment offset and update state for snapshotting
            self._offsets[session_id] = self._offsets.get(session_id, 0) + 1
            offset = self._offsets[session_id]
            
            if session_id not in self._states:
                self._states[session_id] = ReplayState(session_id=session_id)
            
            self._states[session_id] = apply_event(self._states[session_id], event_data)
            
            # Check for snapshot triggers
            should_snapshot = (
                offset % SNAPSHOT_INTERVAL == 0 or
                event.type == EventType.CALL_COMPLETED or
                event.type == EventType.CALL_ENDED
            )
            
            if should_snapshot:
                try:
                    snapshot = self._snapshot_service.create_snapshot(self._states[session_id], offset)
                    self._snapshot_service.persist_snapshot(snapshot)
                except Exception:
                    logger.exception(f"Failed to create/persist snapshot for session {session_id}")

    def metrics(self) -> dict:
        """Return operational metrics for the sink."""
        with self._lock:
            return {
                "persisted_event_count": self._persisted_count,
                "sink_errors": self._errors,
                "current_event_log_path": str(self._current_path) if self._current_path else None,
            }

    def flush(self):
        """
        Ensures all buffered writes are flushed to disk.
        Since we use 'with open(path, "a") as f' for every write, 
        this is currently a no-op as the OS handles the close/flush.
        Added for future compatibility with buffered sinks.
        """
        pass

# Global singleton
sink = EventSink()