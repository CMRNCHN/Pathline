from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)

from ..events.event_types import EventType
from ..events.event_bus import bus
from ..events.event_models import OperationalEvent, EventMetadata

class RuntimeState(str, Enum):
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    STALLING = "STALLING"
    DISCONNECTED = "DISCONNECTED"
    RECOVERING = "RECOVERING"
    TERMINATED = "TERMINATED"
    FAILED = "FAILED"
    CLEANED = "CLEANED"

class WebSocketState(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    UNKNOWN = "UNKNOWN"

@dataclass
class SessionRuntimeInfo:
    session_id: str
    call_sid: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    last_heartbeat_at: float = field(default_factory=time.time)
    runtime_state: RuntimeState = RuntimeState.INITIALIZING
    websocket_state: WebSocketState = WebSocketState.UNKNOWN
    cleanup_state: bool = False
    failure_reason: Optional[str] = None
    recovery_attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    thread_id: Optional[int] = None

class RuntimeRegistry:
    """
    Thread-safe registry of active session runtimes.
    """
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionRuntimeInfo] = {}
        self._lock = threading.Lock()

    def add(self, info: SessionRuntimeInfo) -> None:
        with self._lock:
            self._sessions[info.session_id] = info

    def get(self, session_id: str) -> Optional[SessionRuntimeInfo]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> Optional[SessionRuntimeInfo]:
        with self._lock:
            return self._sessions.pop(session_id, None)

    def list_all(self) -> List[SessionRuntimeInfo]:
        with self._lock:
            return list(self._sessions.values())

    def __contains__(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

class RuntimeSupervisor:
    """
    Monitors active sessions, detects stalls, and coordinates cleanup.
    Lightweight, single-process, local-first.
    """
    
    RUNTIME_STALL_TIMEOUT_SECONDS = 60
    HEARTBEAT_TIMEOUT_SECONDS = 30
    WEBSOCKET_TIMEOUT_SECONDS = 30
    MAX_RECOVERY_ATTEMPTS = 3

    def __init__(self) -> None:
        self.registry = RuntimeRegistry()
        self._stop_event = threading.Event()
        self._watchdog_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the supervisor and subscribe to relevant events."""
        bus.subscribe(EventType.SESSION_TERMINATE, self._on_terminate_requested)
        bus.subscribe(EventType.HEARTBEAT, self._on_heartbeat)
        self.start_watchdog()

    def _on_terminate_requested(self, event: OperationalEvent) -> None:
        session_id = event.meta.session_id
        if session_id:
            reason = event.payload.get("reason", "event_requested_termination")
            self.terminate_session(session_id, reason=reason)

    def _on_heartbeat(self, event: OperationalEvent) -> None:
        session_id = event.meta.session_id
        if session_id:
            info = self.registry.get(session_id)
            if info:
                info.last_heartbeat_at = time.time()
                info.last_activity_at = time.time()

    def register_session(self, session_id: str, call_sid: Optional[str] = None) -> None:
        info = SessionRuntimeInfo(
            session_id=session_id,
            call_sid=call_sid,
            runtime_state=RuntimeState.ACTIVE,
            websocket_state=WebSocketState.CONNECTED,
            thread_id=threading.get_ident()
        )
        self.registry.add(info)
        bus.publish(OperationalEvent(
            type=EventType.CALL_STARTED,
            payload={"stage": "supervisor_registered", "call_sid": call_sid},
            meta=EventMetadata(session_id=session_id, source_component="supervisor")
        ))

    def record_heartbeat(self, session_id: str) -> None:
        """Publishes a heartbeat event for a session."""
        info = self.registry.get(session_id)
        if info:
            bus.publish(OperationalEvent(
                type=EventType.HEARTBEAT,
                payload={"call_sid": info.call_sid},
                meta=EventMetadata(session_id=session_id, source_component="supervisor")
            ))

    def supervised_session(self, session_id: str, task: Callable, *args, **kwargs) -> Any:
        """
        Runs a session task within a supervised boundary.
        Captures exceptions and ensures lifecycle events are emitted.
        """
        call_sid = kwargs.pop("call_sid", None)
        self.register_session(session_id, call_sid=call_sid)
        try:
            return task(*args, **kwargs)
        except Exception as e:
            logger.error(f"Supervised session {session_id} failed: {e}")
            self.report_failure(session_id, reason=str(e))
            raise
        finally:
            # Note: termination might have already happened via event or explicit call
            # but we ensure the supervisor knows it's ending and triggers cleanup.
            info = self.registry.get(session_id)
            if info:
                if info.runtime_state not in (RuntimeState.TERMINATED, RuntimeState.FAILED, RuntimeState.CLEANED):
                    self.terminate_session(session_id, reason="supervised_task_completed")
                
                from .session_cleanup import cleanup_manager
                cleanup_manager.cleanup_session(session_id, reason="supervised_run_cleanup")

    def update_activity(self, session_id: str, websocket_connected: bool = True) -> None:
        info = self.registry.get(session_id)
        if info:
            info.last_activity_at = time.time()
            
            prev_ws_state = info.websocket_state
            info.websocket_state = WebSocketState.CONNECTED if websocket_connected else WebSocketState.DISCONNECTED
            
            if prev_ws_state == WebSocketState.DISCONNECTED and info.websocket_state == WebSocketState.CONNECTED:
                bus.publish(OperationalEvent(
                    type=EventType.WEBSOCKET_RECONNECTED,
                    payload={"call_sid": info.call_sid},
                    meta=EventMetadata(session_id=session_id, source_component="supervisor")
                ))
                if info.runtime_state == RuntimeState.DISCONNECTED:
                    self._transition_state(info, RuntimeState.RECOVERING)
            elif prev_ws_state == WebSocketState.CONNECTED and info.websocket_state == WebSocketState.DISCONNECTED:
                bus.publish(OperationalEvent(
                    type=EventType.WEBSOCKET_DISCONNECTED,
                    payload={"call_sid": info.call_sid},
                    meta=EventMetadata(session_id=session_id, source_component="supervisor")
                ))
                self._transition_state(info, RuntimeState.DISCONNECTED)

    def report_failure(self, session_id: str, reason: str) -> None:
        info = self.registry.get(session_id)
        if info:
            info.failure_reason = reason
            self._transition_state(info, RuntimeState.FAILED)
            bus.publish(OperationalEvent(
                type=EventType.ERROR_RAISED,
                payload={"error": reason, "call_sid": info.call_sid},
                meta=EventMetadata(session_id=session_id, source_component="supervisor")
            ))

    def terminate_session(self, session_id: str, reason: str = "normal_termination") -> None:
        info = self.registry.get(session_id)
        if info:
            self._transition_state(info, RuntimeState.TERMINATED)
            bus.publish(OperationalEvent(
                type=EventType.SESSION_TERMINATED,
                payload={"reason": reason, "call_sid": info.call_sid},
                meta=EventMetadata(session_id=session_id, source_component="supervisor")
            ))

    def _transition_state(self, info: SessionRuntimeInfo, new_state: RuntimeState) -> None:
        old_state = info.runtime_state
        if old_state == new_state:
            return
            
        info.runtime_state = new_state
        # Emit state transition event for deterministic lineage
        bus.publish(OperationalEvent(
            type="RUNTIME_STATE_TRANSITION",
            payload={
                "old_state": old_state,
                "new_state": new_state,
                "call_sid": info.call_sid,
                "t_ms": int((time.time() - info.started_at) * 1000)
            },
            meta=EventMetadata(session_id=info.session_id, source_component="supervisor")
        ))

    def get_session_info(self, session_id: str) -> Optional[SessionRuntimeInfo]:
        return self.registry.get(session_id)

    def get_health_snapshot(self) -> Dict[str, Any]:
        state_counts = {}
        for state in RuntimeState:
            state_counts[state.value] = 0
        
        stalled_sessions = 0
        recovery_attempts = 0
        websocket_disconnects = 0
        
        sessions = self.registry.list_all()
        for info in sessions:
            state_counts[info.runtime_state.value] += 1
            if info.runtime_state == RuntimeState.STALLING:
                stalled_sessions += 1
            recovery_attempts += info.recovery_attempts
            if info.websocket_state == WebSocketState.DISCONNECTED:
                websocket_disconnects += 1

        return {
            "active_sessions": len([s for s in sessions if s.runtime_state == RuntimeState.ACTIVE]),
            "stalled_sessions": stalled_sessions,
            "recovery_attempts": recovery_attempts,
            "websocket_disconnects": websocket_disconnects,
            "cleanup_operations": len([s for s in sessions if s.cleanup_state]),
            "runtime_state_counts": state_counts
        }

    def start_watchdog(self, interval: float = 5.0) -> None:
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return
            
        self._stop_event.clear()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop, 
            args=(interval,), 
            name="RuntimeSupervisorWatchdog",
            daemon=True
        )
        self._watchdog_thread.start()

    def stop_watchdog(self) -> None:
        self._stop_event.set()
        if self._watchdog_thread:
            self._watchdog_thread.join(timeout=2.0)

    def _watchdog_loop(self, interval: float) -> None:
        while not self._stop_event.is_set():
            try:
                self._check_sessions()
            except Exception as e:
                # Local logging only, don't crash the watchdog
                print(f"Supervisor watchdog error: {e}")
            time.sleep(interval)

    def _check_sessions(self) -> None:
        now = time.time()
        for info in self.registry.list_all():
            # Check for stalled sessions (no activity)
            if info.runtime_state == RuntimeState.ACTIVE:
                if now - info.last_activity_at > self.RUNTIME_STALL_TIMEOUT_SECONDS:
                    self._transition_state(info, RuntimeState.STALLING)
                    bus.publish(OperationalEvent(
                        type=EventType.RUNTIME_STALLED,
                        payload={"reason": "activity_timeout", "call_sid": info.call_sid},
                        meta=EventMetadata(session_id=info.session_id, source_component="supervisor")
                    ))
                elif now - info.last_heartbeat_at > self.HEARTBEAT_TIMEOUT_SECONDS:
                    # Missing heartbeats but maybe still some activity? 
                    # Usually heartbeat is the most frequent.
                    pass

            # Bounded cleanup for terminated/failed sessions
            if info.runtime_state in (RuntimeState.TERMINATED, RuntimeState.FAILED) and not info.cleanup_state:
                from .session_cleanup import cleanup_manager
                cleanup_manager.cleanup_session(info.session_id, reason="watchdog_auto_cleanup")

# Singleton instance
supervisor = RuntimeSupervisor()
