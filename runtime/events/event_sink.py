import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from infrastructure.config.paths import EVENTS_DIR
from runtime.events.event_bus import bus
from runtime.events.event_models import OperationalEvent
from runtime.events.event_types import EventType

logger = logging.getLogger(__name__)

# Event types that are operator-observability telemetry, NOT part of the
# deterministic replay stream. These are persisted to telemetry_<id>.jsonl,
# never to the session_<id>.jsonl replay log. Writing them into the replay
# log corrupts deterministic reconstruction (replay reads session_*.jsonl).
TELEMETRY_EVENT_TYPES = frozenset({EventType.OPERATOR_ACTION})

# Filename prefixes for the two append-only streams.
REPLAY_LOG_PREFIX = "session_"
TELEMETRY_LOG_PREFIX = "telemetry_"


class ReplayContaminationError(RuntimeError):
    """Raised when a telemetry event is about to be written into the replay log.

    This is the hard guardrail protecting replay determinism: the replay
    reconstructor reads only session_<id>.jsonl, so any telemetry event that
    reaches that path would silently corrupt deterministic replay.
    """


class EventSink:
    """
    Persists OperationalEvents to append-only JSONL files.

    Two separate streams, split by event class:
      - session_<id>.jsonl    — deterministic replay events (immutable input
                                 for reconstruction; telemetry never lands here)
      - telemetry_<id>.jsonl  — operator-observability events (OPERATOR_ACTION)
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
        """Write the event to the appropriate append-only JSONL file.

        Telemetry events (OPERATOR_ACTION) are routed to telemetry_<id>.jsonl;
        all replay-relevant events go to session_<id>.jsonl. The split keeps the
        replay log immutable with respect to operator observability.
        """
        session_id = event.meta.session_id or "unknown_session"
        is_telemetry = event.type in TELEMETRY_EVENT_TYPES
        prefix = TELEMETRY_LOG_PREFIX if is_telemetry else REPLAY_LOG_PREFIX

        date_str = datetime.fromtimestamp(event.meta.timestamp).strftime("%Y-%m-%d")
        dir_path = self.base_dir / date_str
        file_path = dir_path / f"{prefix}{session_id}.jsonl"

        # Hard guardrail (defense in depth): regardless of routing above, a
        # telemetry event must never be written into the replay log.
        if event.type in TELEMETRY_EVENT_TYPES and file_path.name.startswith(REPLAY_LOG_PREFIX):
            raise ReplayContaminationError(
                f"Refusing to write telemetry event {event.type} into replay log "
                f"{file_path.name} — would corrupt deterministic replay."
            )

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
            if not is_telemetry:
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
