"""Runtime event types for the IVR run suite system.

Two categories:
  1. IVRRuntimeEvent — events emitted by the existing IVR runtime (transcript,
     intent, node, secure card, call lifecycle). These are produced by the
     streaming server and routing engine, and consumed by the SuiteRunner.

  2. RunSuiteEvent — events emitted by the SuiteRunner itself to update the UI
     about step progress, scenario completion, etc.

All events are plain dataclasses so they serialize cleanly to JSON.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any

from tests.run_suites.status import StepStatus
from runtime.events.event_models import OperationalEvent, EventMetadata


# ─── IVR Runtime Event Types (string constants) ───────────────────────────────

class IVREventType:
    # Transcript
    TRANSCRIPT_PARTIAL = "TranscriptPartial"
    TRANSCRIPT_FINAL = "TranscriptFinal"

    # Intent / routing
    INTENT_DETECTED = "IntentDetected"
    INTENT_REJECTED = "IntentRejected"
    ROUTE_NODE_ENTERED = "RouteNodeEntered"
    ROUTE_NODE_COMPLETED = "RouteNodeCompleted"

    # Actions
    ACTION_REQUESTED = "ActionRequested"
    ACTION_COMPLETED = "ActionCompleted"

    # TTS / Twilio
    TTS_REQUESTED = "TTSRequested"
    TWILIO_RESPONSE_READY = "TwilioResponseReady"

    # Secure card
    SECURE_CARD_STORED = "SecureCardStored"
    SECURE_CARD_LOOKUP = "SecureCardLookup"
    SECURE_CARD_DELETED = "SecureCardDeleted"

    # Call lifecycle
    CALL_STARTED = "CallStarted"
    CALL_TRANSFERRED = "CallTransferred"
    CALL_ENDED = "CallEnded"

    # Errors
    ERROR_RAISED = "ErrorRaised"


@dataclass
class IVRRuntimeEvent:
    """A single event from the IVR runtime, delivered to the SuiteRunner."""
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def get(self, key: str, default: Any = None) -> Any:
        return self.payload.get(key, default)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


# ─── Run Suite Events (emitted by SuiteRunner → UI) ──────────────────────────

@dataclass
class RunSuiteEvent:
    """Base event emitted by the SuiteRunner for UI consumption."""
    type: str
    suite_id: str
    timestamp: float = field(default_factory=time.time)
    meta: EventMetadata = field(default_factory=EventMetadata)

    def as_operational_event(self) -> OperationalEvent:
        """Convert to the unified OperationalEvent model."""
        # Update metadata with suite_id if not present
        if not self.meta.session_id:
            object.__setattr__(self.meta, 'session_id', self.suite_id)
        
        return OperationalEvent(
            type=self.type,
            payload={k: v for k, v in self.as_dict().items() if k not in ('type', 'meta', 'timestamp')},
            meta=self.meta
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def as_ws_message(self) -> dict[str, Any]:
        """Format for WebSocket/poll delivery to browser."""
        d = self.as_dict()
        return d


@dataclass
class RunSuiteStartedEvent(RunSuiteEvent):
    type: str = field(default="RunSuiteStarted", init=False)
    run_id: str = ""
    name: str = ""
    scenario_count: int = 0


@dataclass
class RunSuiteCompletedEvent(RunSuiteEvent):
    type: str = field(default="RunSuiteCompleted", init=False)
    run_id: str = ""
    pass_count: int = 0
    fail_count: int = 0
    timeout_count: int = 0
    duration_ms: float = 0.0
    status: str = "passed"


@dataclass
class ScenarioStartedEvent(RunSuiteEvent):
    type: str = field(default="ScenarioStarted", init=False)
    scenario_id: str = ""
    name: str = ""
    step_count: int = 0


@dataclass
class ScenarioCompletedEvent(RunSuiteEvent):
    type: str = field(default="ScenarioCompleted", init=False)
    scenario_id: str = ""
    passed: bool = True
    duration_ms: float = 0.0
    pass_count: int = 0
    fail_count: int = 0


@dataclass
class StepStartedEvent(RunSuiteEvent):
    type: str = field(default="StepStarted", init=False)
    scenario_id: str = ""
    step_id: str = ""
    action: str = ""


@dataclass
class StepUpdatedEvent(RunSuiteEvent):
    type: str = field(default="StepUpdated", init=False)
    scenario_id: str = ""
    step_id: str = ""
    status: str = StepStatus.RUNNING.value
    expected: str | None = None
    actual: str | None = None
    duration_ms: float | None = None
    confidence: float | None = None
    error: str | None = None
    node_id: str | None = None
    transcript_snippet: str | None = None
    secure_card_token: str | None = None


@dataclass
class StepPassedEvent(RunSuiteEvent):
    type: str = field(default="StepPassed", init=False)
    scenario_id: str = ""
    step_id: str = ""
    duration_ms: float = 0.0
    actual: str | None = None
    confidence: float | None = None


@dataclass
class StepFailedEvent(RunSuiteEvent):
    type: str = field(default="StepFailed", init=False)
    scenario_id: str = ""
    step_id: str = ""
    duration_ms: float = 0.0
    reason: str = ""
    expected: str | None = None
    actual: str | None = None
    error: str | None = None


@dataclass
class StepTimedOutEvent(RunSuiteEvent):
    type: str = field(default="StepTimedOut", init=False)
    scenario_id: str = ""
    step_id: str = ""
    timeout_ms: int = 0