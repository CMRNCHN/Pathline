from __future__ import annotations

from runtime.supervision.runtime_supervisor import RuntimeState
from runtime.events.event_types import EventType
from runtime.events.event_bus import bus
from runtime.events.event_models import OperationalEvent, EventMetadata

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
        Bounded at MAX_RECOVERY_ATTEMPTS (3).
        """
        from runtime.supervision.runtime_supervisor import supervisor
        info = supervisor.get_session_info(session_id)
        if not info:
            return False

        if info.recovery_attempts >= self.max_attempts:
            action_message = "Operator: Session recovery exhausted. Manual restart required."
            bus.publish(OperationalEvent(
                type=EventType.RECOVERY_FAILED,
                payload={
                    "reason": "max_attempts_exceeded",
                    "attempt_count": info.recovery_attempts,
                    "max_attempts": self.max_attempts,
                    "call_sid": info.call_sid,
                    "action_expected": action_message
                },
                meta=EventMetadata(session_id=session_id, source_component="recovery_manager")
            ))
            supervisor.report_failure(session_id, action_message)
            from runtime.sessions.session_cleanup import cleanup_manager
            cleanup_manager.cleanup_session(session_id, reason="recovery_exhausted")
            return False

        info.recovery_attempts += 1

        bus.publish(OperationalEvent(
            type="RECOVERY_ATTEMPTED",
            payload={
                "attempt": info.recovery_attempts,
                "max_attempts": self.max_attempts,
                "call_sid": info.call_sid,
                "action_expected": f"Waiting for activity (attempt {info.recovery_attempts}/{self.max_attempts})"
            },
            meta=EventMetadata(session_id=session_id, source_component="recovery_manager")
        ))

        return True

    def mark_recovered(self, session_id: str) -> None:
        from runtime.supervision.runtime_supervisor import supervisor
        info = supervisor.get_session_info(session_id)
        if info and info.runtime_state == RuntimeState.RECOVERING:
            bus.publish(OperationalEvent(
                type=EventType.SESSION_RECOVERED,
                payload={"call_sid": info.call_sid},
                meta=EventMetadata(session_id=session_id, source_component="recovery_manager")
            ))

# Singleton instance
recovery_manager = RecoveryManager()