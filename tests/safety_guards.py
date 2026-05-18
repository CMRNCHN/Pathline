import time
from typing import Dict, Any
from runtime.events.event_types import EventType
from runtime.events.event_bus import bus as EventBus
from runtime.events.event_models import OperationalEvent, EventMetadata
from tests.telecom_test_plan import TelecomTestPlan

class SafetyGuards:
    def __init__(self, plan: TelecomTestPlan, session_id: str):
        self.plan = plan
        self.session_id = session_id
        self.start_time = time.time()
        self.dtmf_count = 0
        self.max_depth_seen = 0
        self.last_audio_at = time.time()
        self.last_transcript_at = time.time()
        self._triggered = False
        self._reason = ""

    def check_duration(self) -> bool:
        elapsed = time.time() - self.start_time
        if elapsed > self.plan.max_duration_seconds:
            self._trigger("duration exceeded", {"elapsed": elapsed, "limit": self.plan.max_duration_seconds})
            return False
        return True

    def check_dtmf(self, count: int) -> bool:
        self.dtmf_count = count
        if self.dtmf_count > self.plan.max_dtmf_actions:
            self._trigger("dtmf limit exceeded", {"count": self.dtmf_count, "limit": self.plan.max_dtmf_actions})
            return False
        return True

    def check_depth(self, depth: int) -> bool:
        self.max_depth_seen = max(self.max_depth_seen, depth)
        if depth > self.plan.max_depth:
            self._trigger("depth exceeded", {"depth": depth, "limit": self.plan.max_depth})
            return False
        return True

    def report_audio(self):
        self.last_audio_at = time.time()

    def report_transcript(self):
        self.last_transcript_at = time.time()

    def check_timeouts(self, audio_timeout: float = 30.0, transcript_timeout: float = 60.0) -> bool:
        now = time.time()
        if now - self.last_audio_at > audio_timeout:
            self._trigger("no audio timeout", {"idle_seconds": now - self.last_audio_at})
            return False
        # Only check transcript timeout if we expect one (e.g. after initial prompt)
        # For now, keeping it simple as per requirements.
        return True

    def check_transfer(self, transfer_detected: bool) -> bool:
        if transfer_detected and self.plan.stop_on_transfer:
            self._trigger("transfer detected", {})
            return False
        return True

    def check_confidence(self, confidence: float, threshold: float = 0.5) -> bool:
        if self.plan.stop_on_low_confidence and confidence < threshold:
            self._trigger("low confidence", {"confidence": confidence, "threshold": threshold})
            return False
        return True

    def _trigger(self, reason: str, detail: Dict[str, Any]):
        if not self._triggered:
            self._triggered = True
            self._reason = reason
            EventBus.publish(OperationalEvent(
                type=EventType.SAFETY_GUARD_TRIGGERED,
                payload={
                    "reason": reason,
                    "detail": detail,
                    "test_id": self.plan.test_id
                },
                meta=EventMetadata(
                    session_id=self.session_id,
                    source_component="safety_guards"
                )
            ))

    @property
    def triggered(self) -> bool:
        return self._triggered

    @property
    def reason(self) -> str:
        return self._reason