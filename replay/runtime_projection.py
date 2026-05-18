from __future__ import annotations

import logging
from typing import Dict

from infrastructure.config.paths import SNAPSHOT_INTERVAL
from replay.reducers.replay_reducer import apply_event
from replay.snapshots.snapshot_service import SnapshotService
from runtime.events.event_bus import bus
from runtime.events.event_models import OperationalEvent
from runtime.events.event_types import EventType
from runtime.state.replay_state import ReplayState

logger = logging.getLogger(__name__)


class ReplayProjection:
    """Maintains replay state and snapshots from operational events."""

    def __init__(self) -> None:
        self._states: Dict[str, ReplayState] = {}
        self._offsets: Dict[str, int] = {}
        self._snapshot_service = SnapshotService()

    def start(self) -> None:
        bus.subscribe_all(self.on_event)
        logger.info("ReplayProjection started and subscribed to EventBus")

    def on_event(self, event: OperationalEvent) -> None:
        session_id = event.meta.session_id or "unknown_session"

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

        self._offsets[session_id] = self._offsets.get(session_id, 0) + 1
        offset = self._offsets[session_id]

        if session_id not in self._states:
            self._states[session_id] = ReplayState(session_id=session_id)

        self._states[session_id] = apply_event(self._states[session_id], event_data)

        should_snapshot = (
            offset % SNAPSHOT_INTERVAL == 0
            or event.type == EventType.CALL_COMPLETED
            or event.type == EventType.CALL_ENDED
        )

        if should_snapshot:
            try:
                snapshot = self._snapshot_service.create_snapshot(self._states[session_id], offset)
                self._snapshot_service.persist_snapshot(snapshot)
            except Exception:
                logger.exception("Failed to create/persist snapshot for session %s", session_id)


projection = ReplayProjection()
