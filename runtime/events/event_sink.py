import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from infrastructure.config.paths import EVENTS_DIR
from runtime.events.event_bus import bus
from runtime.events.event_models import OperationalEvent

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

    def start(self):
        """Subscribe to the event bus and start persisting events."""
        bus.subscribe_all(self.on_event)
        logger.info("EventSink started and subscribed to EventBus")

    def stop(self):
        """Unsubscribe from the event bus."""
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
                "payload": event.payload,
            }

            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_data) + "\n")

            self._persisted_count += 1
            self._current_path = file_path
            self._active_files[session_id] = file_path

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


sink = EventSink()
