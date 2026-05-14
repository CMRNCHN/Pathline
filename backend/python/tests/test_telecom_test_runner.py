import time
import threading
from ivr_assessor.testing.telecom_test_plan import TelecomTestPlan
from ivr_assessor.testing.telecom_test_runner import TelecomTestRunner
from ivr_assessor.testing.telecom_test_result import TestOutcome
from ivr_assessor.backend.ui.ui_state import STATE

def test_runner_initialization():
    plan = TelecomTestPlan(
        test_id="runner-test",
        name="Runner Test",
        target_label="Target",
        target_number_ref="REF1",
        max_duration_seconds=10,
        max_depth=5,
        max_dtmf_actions=3
    )
    runner = TelecomTestRunner(plan)
    assert runner.plan == plan
    assert runner.result is None
    assert runner.guards is None

def test_runner_abort():
    plan = TelecomTestPlan(
        test_id="abort-test",
        name="Abort Test",
        target_label="Target",
        target_number_ref="REF1",
        max_duration_seconds=60,
        max_depth=5,
        max_dtmf_actions=3
    )
    runner = TelecomTestRunner(plan)
    
    # Mocking result for abort to work without full run
    from ivr_assessor.testing.telecom_test_result import TelecomTestResult
    runner.result = TelecomTestResult(test_id=plan.test_id, session_id="sess-1", started_at=time.time())
    
    runner.abort()
    assert runner.result.outcome == TestOutcome.ABORTED
    assert runner.result.safety_stop_reason == "Operator abort"

def test_runner_timeout_guard():
    plan = TelecomTestPlan(
        test_id="timeout-test",
        name="Timeout Test",
        target_label="Target",
        target_number_ref="REF1",
        max_duration_seconds=1, # Very short
        max_depth=5,
        max_dtmf_actions=3
    )
    runner = TelecomTestRunner(plan)
    
    def mock_session_thread(*args, **kwargs):
        STATE.is_running = True
        time.sleep(2)
        STATE.is_running = False

    # We need to run this in a thread because it has a loop
    run_thread = threading.Thread(target=runner.run, args=(mock_session_thread, {"target": "+123"}))
    run_thread.start()
    run_thread.join(timeout=5)
    
    assert runner.result.outcome == TestOutcome.TIMED_OUT
    assert "duration exceeded" in runner.result.safety_stop_reason.lower()
