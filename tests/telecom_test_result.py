from dataclasses import dataclass
from typing import Optional
from enum import Enum

class TestOutcome(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ABORTED = "ABORTED"
    TIMED_OUT = "TIMED_OUT"
    TRANSFER_STOPPED = "TRANSFER_STOPPED"
    LOW_CONFIDENCE_STOPPED = "LOW_CONFIDENCE_STOPPED"

@dataclass
class TelecomTestResult:
    test_id: str
    session_id: str
    started_at: float
    ended_at: Optional[float] = None
    outcome: Optional[TestOutcome] = None
    failure_reason: Optional[str] = None
    events_count: int = 0
    states_discovered: int = 0
    unresolved_count: int = 0
    transcript_available: bool = False
    recording_available: bool = False
    replay_available: bool = False
    snapshot_available: bool = False
    operator_abort: bool = False
    safety_stop_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "test_id": self.test_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "outcome": self.outcome.value if self.outcome else None,
            "failure_reason": self.failure_reason,
            "events_count": self.events_count,
            "states_discovered": self.states_discovered,
            "unresolved_count": self.unresolved_count,
            "transcript_available": self.transcript_available,
            "recording_available": self.recording_available,
            "replay_available": self.replay_available,
            "snapshot_available": self.snapshot_available,
            "operator_abort": self.operator_abort,
            "safety_stop_reason": self.safety_stop_reason
        }