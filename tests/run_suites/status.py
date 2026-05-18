"""Step and suite status enums with valid transition rules."""
from __future__ import annotations

from enum import Enum


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    RETRYING = "retrying"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"
    ERRORED = "errored"


class SuiteRunStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"
    ABORTED = "aborted"


class FailureReason(str, Enum):
    TEXT_MISMATCH = "text_mismatch"
    EVENT_MISMATCH = "event_mismatch"
    INTENT_MISMATCH = "intent_mismatch"
    NODE_MISMATCH = "node_mismatch"
    TIMEOUT = "timeout"
    PAN_LEAKED = "pan_leaked"
    SECURE_CARD_MISSING = "secure_card_missing"
    SECURE_CARD_NOT_DELETED = "secure_card_not_deleted"
    WEBHOOK_NOT_CALLED = "webhook_not_called"
    CALL_ERROR = "call_error"
    UNKNOWN = "unknown"


# Valid transitions: from_status -> set of allowed to_statuses
_TRANSITIONS: dict[StepStatus, set[StepStatus]] = {
    StepStatus.PENDING:   {StepStatus.RUNNING, StepStatus.SKIPPED},
    StepStatus.RUNNING:   {StepStatus.PASSED, StepStatus.FAILED, StepStatus.TIMED_OUT,
                           StepStatus.ERRORED, StepStatus.RETRYING},
    StepStatus.RETRYING:  {StepStatus.RUNNING, StepStatus.FAILED, StepStatus.TIMED_OUT,
                           StepStatus.ERRORED},
    StepStatus.PASSED:    set(),
    StepStatus.FAILED:    set(),
    StepStatus.TIMED_OUT: set(),
    StepStatus.SKIPPED:   set(),
    StepStatus.ERRORED:   set(),
}

# Terminal states — once entered, no further transitions are allowed.
TERMINAL_STATUSES: frozenset[StepStatus] = frozenset({
    StepStatus.PASSED,
    StepStatus.FAILED,
    StepStatus.TIMED_OUT,
    StepStatus.SKIPPED,
    StepStatus.ERRORED,
})


def is_valid_transition(from_status: StepStatus, to_status: StepStatus) -> bool:
    return to_status in _TRANSITIONS.get(from_status, set())


def is_terminal(status: StepStatus) -> bool:
    return status in TERMINAL_STATUSES