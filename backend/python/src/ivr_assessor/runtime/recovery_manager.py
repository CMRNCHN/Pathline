from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .runtime_supervisor import supervisor, RuntimeState
from ..events.event_types import EventType
from ..events.event_bus import bus
from ..events.event_models import OperationalEvent, EventMetadata

class RecoveryManager:
    """
    Coordinates session recovery attempts.
    Bounded, deterministic, and replay-visible.
    """

    def __init__(self, max_attempts: int = 3) -> None:
        self.max_attempts = max_attempts

    def attempt_recovery(self, session_id: str) -> bool:
        """
        Attempts to recover a stalled or disconnected session.
        Returns True if recovery was initiated, False if max attempts reached.
        """
        from .runtime_supervisor import supervisor
        info = supervisor.get_session_info(session_id)
        if not info:
            return False

        if info.recovery_attempts >= self.max_attempts:
            bus.publish(OperationalEvent(
                type=EventType.RECOVERY_FAILED,
                payload={"reason": "max_attempts_exceeded", "call_sid": info.call_sid},
                meta=EventMetadata(session_id=session_id, source_component="recovery_manager")
            ))
            supervisor.report_failure(session_id, "Recovery failed: max attempts reached")
            return False

        info.recovery_attempts += 1
        
        bus.publish(OperationalEvent(
            type="RECOVERY_ATTEMPTED",
            payload={
                "attempt": info.recovery_attempts,
                "max_attempts": self.max_attempts,
                "call_sid": info.call_sid
            },
            meta=EventMetadata(session_id=session_id, source_component="recovery_manager")
        ))
        
        # We don't transition to ACTIVE yet; we transition to RECOVERING 
        # to see if it actually recovers.
        # supervisor._transition_state is internal, but supervisor.update_activity 
        # will handle the transition back to ACTIVE if it gets a signal.
        
        return True

    def mark_recovered(self, session_id: str) -> None:
        from .runtime_supervisor import supervisor
        info = supervisor.get_session_info(session_id)
        if info and info.runtime_state == RuntimeState.RECOVERING:
            bus.publish(OperationalEvent(
                type=EventType.SESSION_RECOVERED,
                payload={"call_sid": info.call_sid},
                meta=EventMetadata(session_id=session_id, source_component="recovery_manager")
            ))

# Singleton instance
recovery_manager = RecoveryManager()
