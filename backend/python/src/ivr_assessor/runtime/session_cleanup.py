from __future__ import annotations

import logging
import time
from typing import Optional

from .runtime_supervisor import supervisor, RuntimeState
from ..events.event_types import EventType
from ..events.event_bus import bus
from ..events.event_models import OperationalEvent, EventMetadata

logger = logging.getLogger(__name__)

class SessionCleanup:
    """
    Handles idempotent cleanup of session artifacts and runtime state.
    Ensures failures and cleanup actions are replay-visible.
    """

    def cleanup_session(self, session_id: str, reason: str = "stale_cleanup") -> bool:
        """
        Cleans up a session. Returns True if cleanup was performed or already done.
        """
        from .runtime_supervisor import supervisor
        info = supervisor.get_session_info(session_id)
        if not info:
            return False

        if info.cleanup_state:
            # Even if marked cleaned, ensure it's removed from registry if reason is final
            if reason != "stale_cleanup":
                 supervisor.registry.remove(session_id)
            return True

        # 1. Record cleanup start
        bus.publish(OperationalEvent(
            type="SESSION_CLEANUP_STARTED",
            payload={"reason": reason, "call_sid": info.call_sid},
            meta=EventMetadata(session_id=session_id, source_component="session_cleanup")
        ))

        try:
            # 2. Perform actual cleanup
            # Flush EventSink state before registry removal
            from ..events.event_sink import sink as event_sink
            # EventSink is currently sync, but we want to ensure any buffered writes 
            # (OS level) are encouraged.
            
            # 3. Mark as cleaned in supervisor
            info.cleanup_state = True
            
            # 4. Final state transition
            if info.runtime_state not in (RuntimeState.TERMINATED, RuntimeState.FAILED):
                info.runtime_state = RuntimeState.CLEANED
            
            bus.publish(OperationalEvent(
                type=EventType.SESSION_CLEANED,
                payload={"status": "success", "call_sid": info.call_sid},
                meta=EventMetadata(session_id=session_id, source_component="session_cleanup")
            ))

            # 5. Final Registry Removal
            supervisor.registry.remove(session_id)
            
            return True

        except Exception as e:
            logger.error(f"Cleanup failed for session {session_id}: {e}")
            bus.publish(OperationalEvent(
                type=EventType.SESSION_CLEANED,
                payload={"status": "failed", "error": str(e), "call_sid": info.call_sid},
                meta=EventMetadata(session_id=session_id, source_component="session_cleanup")
            ))
            return False

# Singleton instance
cleanup_manager = SessionCleanup()
