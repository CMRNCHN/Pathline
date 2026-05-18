import threading
import time
import uuid
from typing import Callable, Optional, Dict, Any

from runtime.events.event_types import EventType
from runtime.events.event_bus import bus as EventBus
from runtime.events.event_models import OperationalEvent, EventMetadata
from analyst.backend.ui.ui_state import STATE
from tests.telecom_test_plan import TelecomTestPlan
from tests.telecom_test_result import TelecomTestResult, TestOutcome
from tests.safety_guards import SafetyGuards
from tests.evidence_manifest import EvidenceManifest

class TelecomTestRunner:
    def __init__(self, plan: TelecomTestPlan):
        self.plan = plan
        self.result: Optional[TelecomTestResult] = None
        self.guards: Optional[SafetyGuards] = None
        self._stop_event = threading.Event()
        self._session_id: Optional[str] = None

    def run(self, session_thread_fn: Callable, start_args: Dict[str, Any]):
        """
        Runs one bounded telecom validation test.
        """
        self.result = TelecomTestResult(
            test_id=self.plan.test_id,
            session_id=str(uuid.uuid4()), # We generate a session ID for the test
            started_at=time.time()
        )
        self._session_id = self.result.session_id
        self.guards = SafetyGuards(self.plan, self._session_id)

        EventBus.publish(OperationalEvent(
            type=EventType.TELECOM_TEST_STARTED,
            payload=self.plan.to_dict(),
            meta=EventMetadata(session_id=self._session_id, source_component="telecom_test_runner")
        ))

        # Prepare arguments for the session thread
        # We override some settings from the plan
        actual_args = dict(start_args)
        actual_args["manual_mode"] = False # Always auto-pilot for validation test? 
        # Actually, the plan might allow injection but we want deterministic behavior.
        
        # Start existing call flow through existing APIs
        STATE.reset()
        STATE.is_running = True
        
        # We need to make sure the session uses our session_id if possible, 
        # or we capture it when it's created.
        # For now, let's assume session_thread_fn will eventually set STATE.session.
        
        threading.Thread(
            target=session_thread_fn,
            args=(
                actual_args.get("target", ""),
                actual_args.get("user", ""),
                actual_args.get("sid", ""),
                actual_args.get("token", ""),
                actual_args.get("tnum", ""),
                actual_args.get("stream_url"),
                actual_args.get("manual_mode", False)
            ),
            daemon=True
        ).start()

        # Monitoring loop
        try:
            while STATE.is_running and not self._stop_event.is_set():
                if not self.guards.check_duration():
                    self._stop_test(TestOutcome.TIMED_OUT, "Max duration exceeded")
                    break
                
                session = STATE.session
                if session:
                    # Capture session_id if we didn't have it or if it changed
                    if session.session_id and session.session_id != self._session_id:
                         self._session_id = session.session_id
                         self.result.session_id = self._session_id
                         self.guards.session_id = self._session_id

                    # Check other guards
                    # Depth
                    depth = len(session.mapper.graph().get("nodes", [])) # Simple proxy for depth
                    if not self.guards.check_depth(depth):
                         self._stop_test(TestOutcome.FAILED, "Max depth exceeded")
                         break
                    
                    # DTMF actions
                    events = session.ledger.all()
                    dtmf_count = sum(1 for e in events if e.kind == "action" and e.text.startswith("dtmf:"))
                    if not self.guards.check_dtmf(dtmf_count):
                        self._stop_test(TestOutcome.FAILED, "Max DTMF actions exceeded")
                        break
                    
                    # Transfer check
                    transfer_detected = any(e.kind == "transfer" for e in events) # Assumption
                    if not self.guards.check_transfer(transfer_detected):
                        self._stop_test(TestOutcome.TRANSFER_STOPPED, "Transfer detected")
                        break
                    
                time.sleep(1.0)
            
            if not STATE.is_running and self.result.outcome is None:
                # Session ended naturally
                self._stop_test(TestOutcome.PASSED, "Session completed naturally")

        except Exception as e:
            self._stop_test(TestOutcome.FAILED, f"Runner error: {str(e)}")
        
        self._finalize_result()

    def abort(self):
        self._stop_event.set()
        self._stop_test(TestOutcome.ABORTED, "Operator abort")

    def _stop_test(self, outcome: TestOutcome, reason: str):
        if self.result.outcome is not None:
            return
        
        self.result.outcome = outcome
        self.result.safety_stop_reason = reason
        self.result.ended_at = time.time()
        
        # Stop the session
        from analyst.backend.routes.mapper_routes import handle_end
        handle_end()

        event_type = EventType.TELECOM_TEST_COMPLETED
        if outcome == TestOutcome.FAILED:
            event_type = EventType.TELECOM_TEST_FAILED
        elif outcome == TestOutcome.ABORTED:
            event_type = EventType.TELECOM_TEST_ABORTED
            
        EventBus.publish(OperationalEvent(
            type=event_type,
            payload={
                "outcome": outcome.value,
                "reason": reason,
                "test_id": self.plan.test_id
            },
            meta=EventMetadata(session_id=self._session_id, source_component="telecom_test_runner")
        ))

    def _finalize_result(self):
        # Update result with final metrics from session
        session = STATE.session
        if session:
            events = session.ledger.all()
            self.result.events_count = len(events)
            self.result.states_discovered = len(session.mapper.graph().get("nodes", []))
            # unresolved_count = ...
            self.result.recording_available = self.plan.recording_required
            self.result.transcript_available = self.plan.transcript_required
            self.result.replay_available = True
            self.result.snapshot_available = True

        # Generate manifest
        manifest = EvidenceManifest(self.plan.test_id, self._session_id)
        summary = {
            "states_discovered": self.result.states_discovered,
            "events_count": self.result.events_count
        }
        manifest_path = manifest.generate(self.result.to_dict(), summary)
        
        EventBus.publish(OperationalEvent(
            type=EventType.TEST_EVIDENCE_READY,
            payload={
                "test_id": self.plan.test_id,
                "manifest_path": manifest_path,
                "session_id": self._session_id
            },
            meta=EventMetadata(session_id=self._session_id, source_component="telecom_test_runner")
        ))