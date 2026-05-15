"""Tests for the run_suites package.

Covers: models, loader, status transitions, validators, runner (mocked),
reports, and WebSocket event formatting.

No real calls are made — all telephony and IVR events are simulated.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
import threading

import pytest

from ivr_assessor.run_suites.events import (
    IVREventType,
    IVRRuntimeEvent,
    RunSuiteStartedEvent,
    StepPassedEvent,
    StepTimedOutEvent,
)
from ivr_assessor.run_suites.loader import (
    import_suite_json,
    export_suite_json,
    load_suite,
    save_suite,
    delete_suite,
    list_suites,
)
from ivr_assessor.run_suites.models import (
    RunSuite,
    TestScenario,
    TestStep,
    StepAction,
    StepResult,
    ScenarioResult,
    RunResult,
    SuiteRunStatus,
)
from ivr_assessor.run_suites.reports import RunReport
from ivr_assessor.run_suites.runner import SuiteRunner
from ivr_assessor.run_suites.status import (
    StepStatus,
    is_valid_transition,
    is_terminal,
)
from ivr_assessor.run_suites.validators import (
    contains_raw_pan,
    validate_text_contains,
    validate_expected_event,
    validate_intent,
    validate_no_pan_in_log,
    validate_secure_card_token,
    validate_secure_card_deleted,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

MINIMAL_SUITE_JSON = {
    "suite_id": "test_suite_001",
    "name": "Test Suite",
    "description": "Unit test suite",
    "scenarios": [
        {
            "scenario_id": "scenario_a",
            "name": "Scenario A",
            "steps": [
                {
                    "step_id": "start",
                    "action": "start_call",
                    "timeout_ms": 5000,
                },
                {
                    "step_id": "wait_welcome",
                    "action": "wait_for_prompt",
                    "expected_text_contains": "press 1",
                    "timeout_ms": 10000,
                },
            ],
        }
    ],
}

BILLING_SUITE_JSON = {
    "suite_id": "billing_regression",
    "name": "Billing Regression Suite",
    "description": "Tests billing menu and secure card capture.",
    "scenarios": [
        {
            "scenario_id": "billing_card_payment",
            "name": "Billing Card Payment Flow",
            "steps": [
                {"step_id": "start", "action": "start_call", "timeout_ms": 5000},
                {
                    "step_id": "welcome_prompt",
                    "action": "wait_for_prompt",
                    "expected_text_contains": "Press 1 for Billing",
                    "timeout_ms": 10000,
                },
                {
                    "step_id": "select_billing",
                    "action": "send_dtmf",
                    "input_value": "1",
                    "expected_event": "IntentDetected",
                    "expected_intent": "billing",
                    "timeout_ms": 5000,
                },
                {
                    "step_id": "verify_no_pan",
                    "action": "check_no_raw_card_logged",
                    "timeout_ms": 5000,
                },
                {"step_id": "end", "action": "end_call", "timeout_ms": 5000},
            ],
        }
    ],
}


def _make_suite() -> RunSuite:
    return RunSuite.from_dict(MINIMAL_SUITE_JSON)


def _make_billing_suite() -> RunSuite:
    return RunSuite.from_dict(BILLING_SUITE_JSON)


# ─── Status enum tests ────────────────────────────────────────────────────────

def test_valid_transition_pending_to_running() -> None:
    assert is_valid_transition(StepStatus.PENDING, StepStatus.RUNNING)


def test_valid_transition_running_to_passed() -> None:
    assert is_valid_transition(StepStatus.RUNNING, StepStatus.PASSED)


def test_valid_transition_running_to_retrying() -> None:
    assert is_valid_transition(StepStatus.RUNNING, StepStatus.RETRYING)


def test_invalid_transition_passed_to_failed() -> None:
    assert not is_valid_transition(StepStatus.PASSED, StepStatus.FAILED)


def test_invalid_transition_failed_to_running() -> None:
    assert not is_valid_transition(StepStatus.FAILED, StepStatus.RUNNING)


def test_terminal_statuses() -> None:
    for s in (StepStatus.PASSED, StepStatus.FAILED, StepStatus.TIMED_OUT,
              StepStatus.SKIPPED, StepStatus.ERRORED):
        assert is_terminal(s), f"{s} should be terminal"


def test_non_terminal_statuses() -> None:
    for s in (StepStatus.PENDING, StepStatus.RUNNING, StepStatus.RETRYING):
        assert not is_terminal(s), f"{s} should not be terminal"


# ─── Models tests ─────────────────────────────────────────────────────────────

def test_teststep_from_dict_valid() -> None:
    step = TestStep.from_dict({
        "step_id": "s1",
        "action": "send_dtmf",
        "input_value": "1",
        "timeout_ms": 5000,
    })
    assert step.step_id == "s1"
    assert step.action == StepAction.SEND_DTMF
    assert step.input_value == "1"


def test_teststep_from_dict_unknown_action() -> None:
    with pytest.raises(ValueError, match="Unknown step action"):
        TestStep.from_dict({"step_id": "x", "action": "fly_to_moon"})


def test_runsuite_roundtrip() -> None:
    suite = _make_suite()
    data = suite.as_dict()
    suite2 = RunSuite.from_dict(data)
    assert suite2.suite_id == suite.suite_id
    assert suite2.name == suite.name
    assert len(suite2.scenarios) == 1
    assert len(suite2.scenarios[0].steps) == 2


def test_runsuite_pass_fail_counts() -> None:
    sc_result = ScenarioResult(scenario_id="sc", name="S")
    sc_result.step_results = [
        StepResult("a", "start_call", StepStatus.PASSED),
        StepResult("b", "wait_for_prompt", StepStatus.FAILED),
        StepResult("c", "end_call", StepStatus.SKIPPED),
    ]
    assert sc_result.pass_count == 1
    assert sc_result.fail_count == 1


def test_runresult_failed_steps() -> None:
    sc = ScenarioResult(scenario_id="sc", name="S")
    sc.step_results = [
        StepResult("ok", "start_call", StepStatus.PASSED),
        StepResult("bad", "wait_for_prompt", StepStatus.TIMED_OUT,
                   error="timeout"),
    ]
    result = RunResult(
        suite_id="s",
        run_id="r",
        name="N",
        started_at=time.time(),
        scenario_results=[sc],
    )
    failed = result.failed_steps
    assert len(failed) == 1
    assert failed[0]["step_id"] == "bad"


# ─── Loader / validation tests ────────────────────────────────────────────────

def test_import_valid_suite() -> None:
    suite = import_suite_json(json.dumps(MINIMAL_SUITE_JSON))
    assert suite.suite_id == "test_suite_001"
    assert len(suite.scenarios) == 1


def test_import_missing_suite_id() -> None:
    bad = {**MINIMAL_SUITE_JSON, "suite_id": ""}
    with pytest.raises(ValueError, match="suite_id"):
        import_suite_json(json.dumps(bad))


def test_import_invalid_suite_id_chars() -> None:
    bad = {**MINIMAL_SUITE_JSON, "suite_id": "bad/path/../traversal"}
    with pytest.raises(ValueError, match="Invalid suite_id"):
        import_suite_json(json.dumps(bad))


def test_import_missing_name() -> None:
    bad = {**MINIMAL_SUITE_JSON, "name": ""}
    with pytest.raises(ValueError, match="name"):
        import_suite_json(json.dumps(bad))


def test_import_empty_scenarios() -> None:
    bad = {**MINIMAL_SUITE_JSON, "scenarios": []}
    with pytest.raises(ValueError, match="at least one scenario"):
        import_suite_json(json.dumps(bad))


def test_import_unknown_action() -> None:
    bad = json.loads(json.dumps(MINIMAL_SUITE_JSON))
    bad["scenarios"][0]["steps"][0]["action"] = "telepathy"
    with pytest.raises(ValueError, match="unknown action"):
        import_suite_json(json.dumps(bad))


def test_import_send_dtmf_missing_input() -> None:
    bad = json.loads(json.dumps(MINIMAL_SUITE_JSON))
    bad["scenarios"][0]["steps"].append({
        "step_id": "dtmf_no_input",
        "action": "send_dtmf",
        "timeout_ms": 5000,
    })
    with pytest.raises(ValueError, match="requires 'input_value'"):
        import_suite_json(json.dumps(bad))


def test_import_duplicate_step_ids() -> None:
    bad = json.loads(json.dumps(MINIMAL_SUITE_JSON))
    bad["scenarios"][0]["steps"].append({
        "step_id": "start",  # duplicate
        "action": "end_call",
        "timeout_ms": 5000,
    })
    with pytest.raises(ValueError, match="Duplicate step_id"):
        import_suite_json(json.dumps(bad))


def test_export_and_reimport() -> None:
    suite = _make_suite()
    exported = export_suite_json(suite)
    reimported = import_suite_json(exported)
    assert reimported.suite_id == suite.suite_id
    assert reimported.scenarios[0].scenario_id == suite.scenarios[0].scenario_id


def test_save_and_load_suite(tmp_path: Path) -> None:
    suite = _make_suite()
    path = save_suite(suite, suites_dir=tmp_path)
    assert path.exists()
    loaded = load_suite(suite.suite_id, suites_dir=tmp_path)
    assert loaded.name == suite.name


def test_list_suites(tmp_path: Path) -> None:
    save_suite(_make_suite(), suites_dir=tmp_path)
    listing = list_suites(suites_dir=tmp_path)
    assert len(listing) == 1
    assert listing[0]["suite_id"] == "test_suite_001"


def test_delete_suite(tmp_path: Path) -> None:
    save_suite(_make_suite(), suites_dir=tmp_path)
    delete_suite("test_suite_001", suites_dir=tmp_path)
    listing = list_suites(suites_dir=tmp_path)
    assert listing == []


# ─── Validator tests ──────────────────────────────────────────────────────────

def test_contains_raw_pan_true() -> None:
    assert contains_raw_pan("Card: 4242424242424242")


def test_contains_raw_pan_false_short() -> None:
    assert not contains_raw_pan("Your code is 1234567")


def test_contains_raw_pan_false_non_luhn() -> None:
    # 16 digits that don't pass Luhn
    assert not contains_raw_pan("1111111111111111")


def test_validate_text_contains_pass() -> None:
    ok, _ = validate_text_contains("Press 1 for Billing", "billing")
    assert ok


def test_validate_text_contains_fail() -> None:
    ok, reason = validate_text_contains("Press 1 for Support", "billing")
    assert not ok
    assert "billing" in reason


def test_validate_text_contains_none() -> None:
    ok, reason = validate_text_contains(None, "billing")
    assert not ok
    assert "No transcript" in reason


def test_validate_expected_event_pass() -> None:
    ok, _ = validate_expected_event("SecureCardStored", "SecureCardStored")
    assert ok


def test_validate_expected_event_fail() -> None:
    ok, reason = validate_expected_event("CallEnded", "SecureCardStored")
    assert not ok
    assert "CallEnded" in reason


def test_validate_intent_case_insensitive() -> None:
    ok, _ = validate_intent("Billing", "billing")
    assert ok


def test_validate_no_pan_in_log_clean() -> None:
    ok, _ = validate_no_pan_in_log(["Hello", "Press 1", "Thank you"])
    assert ok


def test_validate_no_pan_in_log_pan_found() -> None:
    ok, reason = validate_no_pan_in_log(["Card: 4242424242424242"])
    assert not ok
    assert "Raw card" in reason or "raw card" in reason.lower() or "line 1" in reason


def test_validate_secure_card_token_valid() -> None:
    ok, _ = validate_secure_card_token("tok_1234abcd")
    assert ok


def test_validate_secure_card_token_none() -> None:
    ok, reason = validate_secure_card_token(None)
    assert not ok
    assert "No secure card token" in reason


def test_validate_secure_card_token_is_pan() -> None:
    ok, reason = validate_secure_card_token("4242424242424242")
    assert not ok


def test_validate_secure_card_deleted() -> None:
    ok, _ = validate_secure_card_deleted(True)
    assert ok
    ok2, _ = validate_secure_card_deleted(False)
    assert not ok2


# ─── Runner tests (mocked) ────────────────────────────────────────────────────

def _build_runner(suite: RunSuite) -> SuiteRunner:
    return SuiteRunner(suite=suite, telephony=None)


def _inject_transcript(runner: SuiteRunner, text: str, delay: float = 0.05) -> None:
    """Inject a transcript event into the runner after a short delay."""
    def _inject():
        time.sleep(delay)
        runner.push_runtime_event(IVRRuntimeEvent(
            event_type=IVREventType.TRANSCRIPT_FINAL,
            payload={"text": text, "is_final": True, "speech_final": True},
        ))
    threading.Thread(target=_inject, daemon=True).start()


def _inject_event(
    runner: SuiteRunner, event_type: str, payload: dict, delay: float = 0.05
) -> None:
    def _inject():
        time.sleep(delay)
        runner.push_runtime_event(IVRRuntimeEvent(event_type=event_type, payload=payload))
    threading.Thread(target=_inject, daemon=True).start()


def test_runner_happy_path_no_telephony() -> None:
    """Suite with only check_no_raw_card_logged and end_call passes without telephony."""
    suite = RunSuite(
        suite_id="happy",
        name="Happy Path",
        scenarios=[
            TestScenario(
                scenario_id="sc1",
                name="Clean Logs",
                steps=[
                    TestStep(step_id="no_pan", action=StepAction.CHECK_NO_RAW_CARD_LOGGED,
                             timeout_ms=1000),
                    TestStep(step_id="end", action=StepAction.END_CALL, timeout_ms=1000),
                ],
            )
        ],
    )
    runner = _build_runner(suite)
    runner.start()
    runner._thread.join(timeout=5)
    assert runner.run_result is not None
    assert runner.run_result.status == SuiteRunStatus.PASSED


def test_runner_wait_for_prompt_pass() -> None:
    """wait_for_prompt passes when matching transcript arrives."""
    suite = RunSuite(
        suite_id="wfp",
        name="Wait Prompt",
        scenarios=[
            TestScenario(
                scenario_id="sc",
                name="SC",
                steps=[
                    TestStep(
                        step_id="wait",
                        action=StepAction.WAIT_FOR_PROMPT,
                        expected_text_contains="press 1",
                        timeout_ms=2000,
                    ),
                ],
            )
        ],
    )
    runner = _build_runner(suite)
    _inject_transcript(runner, "Please press 1 for billing", delay=0.1)
    runner.start()
    runner._thread.join(timeout=5)
    assert runner.run_result is not None
    assert runner.run_result.status == SuiteRunStatus.PASSED


def test_runner_wait_for_prompt_timeout() -> None:
    """wait_for_prompt times out when no matching transcript arrives."""
    suite = RunSuite(
        suite_id="wfp_timeout",
        name="Timeout Test",
        scenarios=[
            TestScenario(
                scenario_id="sc",
                name="SC",
                steps=[
                    TestStep(
                        step_id="wait",
                        action=StepAction.WAIT_FOR_PROMPT,
                        expected_text_contains="billing",
                        timeout_ms=300,  # very short timeout
                    ),
                ],
            )
        ],
    )
    runner = _build_runner(suite)
    runner.start()
    runner._thread.join(timeout=5)
    assert runner.run_result is not None
    assert runner.run_result.status == SuiteRunStatus.FAILED
    step = runner.run_result.scenario_results[0].step_results[0]
    assert step.status == StepStatus.TIMED_OUT


def test_runner_check_secure_card_saved() -> None:
    """check_secure_card_saved passes when SecureCardStored event arrives with valid token."""
    suite = RunSuite(
        suite_id="sc_saved",
        name="Secure Card",
        scenarios=[
            TestScenario(
                scenario_id="sc",
                name="SC",
                steps=[
                    TestStep(
                        step_id="card",
                        action=StepAction.CHECK_SECURE_CARD_SAVED,
                        timeout_ms=2000,
                    ),
                ],
            )
        ],
    )
    runner = _build_runner(suite)
    _inject_event(runner, IVREventType.SECURE_CARD_STORED, {
        "token": "tok_abc123",
        "brand": "visa",
        "last4": "4242",
        "status": "active",
    }, delay=0.1)
    runner.start()
    runner._thread.join(timeout=5)
    assert runner.run_result is not None
    assert runner.run_result.status == SuiteRunStatus.PASSED
    step = runner.run_result.scenario_results[0].step_results[0]
    assert step.status == StepStatus.PASSED
    assert step.secure_card_token == "tok_abc123"


def test_runner_secure_card_pan_rejected() -> None:
    """check_secure_card_saved fails if token looks like a raw PAN."""
    suite = RunSuite(
        suite_id="sc_pan",
        name="PAN Reject",
        scenarios=[
            TestScenario(
                scenario_id="sc",
                name="SC",
                steps=[
                    TestStep(
                        step_id="card",
                        action=StepAction.CHECK_SECURE_CARD_SAVED,
                        timeout_ms=2000,
                    ),
                ],
            )
        ],
    )
    runner = _build_runner(suite)
    _inject_event(runner, IVREventType.SECURE_CARD_STORED, {
        "token": "4242424242424242",  # raw PAN — should be rejected
    }, delay=0.1)
    runner.start()
    runner._thread.join(timeout=5)
    assert runner.run_result is not None
    assert runner.run_result.status == SuiteRunStatus.FAILED
    step = runner.run_result.scenario_results[0].step_results[0]
    assert step.status == StepStatus.FAILED


def test_runner_check_no_pan_in_logs() -> None:
    """check_no_raw_card_logged fails if a PAN appears in the log."""
    suite = RunSuite(
        suite_id="no_pan",
        name="No PAN",
        scenarios=[
            TestScenario(
                scenario_id="sc",
                name="SC",
                steps=[
                    TestStep(step_id="check", action=StepAction.CHECK_NO_RAW_CARD_LOGGED,
                             timeout_ms=1000),
                ],
            )
        ],
    )
    runner = _build_runner(suite)
    # Inject a PAN into the log directly (simulates a leaky transcript)
    runner._log_lines.append("[transcript] Your card 4242424242424242 has been charged")
    runner.start()
    runner._thread.join(timeout=5)
    assert runner.run_result is not None
    assert runner.run_result.status == SuiteRunStatus.FAILED


def test_runner_poll_events() -> None:
    """poll_events returns emitted step events."""
    suite = RunSuite(
        suite_id="poll",
        name="Poll Test",
        scenarios=[
            TestScenario(
                scenario_id="sc",
                name="SC",
                steps=[
                    TestStep(step_id="end", action=StepAction.END_CALL, timeout_ms=1000),
                ],
            )
        ],
    )
    runner = _build_runner(suite)
    runner.start()
    runner._thread.join(timeout=5)
    events = runner.poll_events()
    types = [e["type"] for e in events]
    assert "RunSuiteStarted" in types
    assert "StepStarted" in types
    assert "StepPassed" in types
    assert "ScenarioCompleted" in types
    assert "RunSuiteCompleted" in types


def test_runner_remaining_steps_skipped_on_failure() -> None:
    """After a step fails, remaining steps are marked skipped."""
    suite = RunSuite(
        suite_id="skip",
        name="Skip Test",
        scenarios=[
            TestScenario(
                scenario_id="sc",
                name="SC",
                steps=[
                    TestStep(step_id="fail_step", action=StepAction.WAIT_FOR_PROMPT,
                             expected_text_contains="xyz", timeout_ms=200),
                    TestStep(step_id="should_skip", action=StepAction.END_CALL,
                             timeout_ms=1000),
                ],
            )
        ],
    )
    runner = _build_runner(suite)
    runner.start()
    runner._thread.join(timeout=5)
    results = runner.run_result.scenario_results[0].step_results
    assert results[0].status == StepStatus.TIMED_OUT
    assert results[1].status == StepStatus.SKIPPED


# ─── Report tests ─────────────────────────────────────────────────────────────

def _make_run_result() -> RunResult:
    sc = ScenarioResult(scenario_id="sc1", name="Test Scenario",
                        started_at=time.time(), completed_at=time.time() + 1)
    sc.step_results = [
        StepResult("start", "start_call", StepStatus.PASSED, duration_ms=120),
        StepResult("wait", "wait_for_prompt", StepStatus.PASSED,
                   actual_response="Press 1 for billing", duration_ms=850),
        StepResult("end", "end_call", StepStatus.PASSED, duration_ms=50),
    ]
    sc.passed = True
    r = RunResult(
        suite_id="billing_regression",
        run_id="abc123",
        name="Billing Regression Suite",
        status=SuiteRunStatus.PASSED,
        started_at=time.time(),
        completed_at=time.time() + 2,
    )
    r.scenario_results = [sc]
    return r


def test_report_json_contains_suite_id() -> None:
    report = RunReport(_make_run_result())
    data = json.loads(report.as_json())
    assert data["suite_id"] == "billing_regression"
    assert data["status"] == "passed"


def test_report_json_has_scenario_results() -> None:
    report = RunReport(_make_run_result())
    data = json.loads(report.as_json())
    assert len(data["scenario_results"]) == 1
    assert data["scenario_results"][0]["scenario_id"] == "sc1"


def test_report_markdown_contains_suite_name() -> None:
    report = RunReport(_make_run_result())
    md = report.as_markdown()
    assert "Billing Regression Suite" in md


def test_report_markdown_contains_step_ids() -> None:
    report = RunReport(_make_run_result())
    md = report.as_markdown()
    assert "start" in md
    assert "wait" in md


def test_report_markdown_shows_passed_status() -> None:
    report = RunReport(_make_run_result())
    md = report.as_markdown()
    assert "PASSED" in md or "passed" in md


def test_report_save(tmp_path: Path) -> None:
    report = RunReport(_make_run_result())
    json_path, md_path = report.save(reports_dir=tmp_path)
    assert json_path.exists()
    assert md_path.exists()
    data = json.loads(json_path.read_text())
    assert data["suite_id"] == "billing_regression"


# ─── WebSocket event formatting ───────────────────────────────────────────────

def test_runsuite_started_event_dict() -> None:
    ev = RunSuiteStartedEvent(
        suite_id="s1",
        run_id="r1",
        name="My Suite",
        scenario_count=3,
    )
    d = ev.as_ws_message()
    assert d["type"] == "RunSuiteStarted"
    assert d["suite_id"] == "s1"
    assert d["run_id"] == "r1"
    assert d["scenario_count"] == 3


def test_step_passed_event_dict() -> None:
    ev = StepPassedEvent(
        suite_id="s1",
        scenario_id="sc1",
        step_id="wait_prompt",
        duration_ms=420.0,
        actual="Press 1 for billing",
    )
    d = ev.as_ws_message()
    assert d["type"] == "StepPassed"
    assert d["step_id"] == "wait_prompt"
    assert d["duration_ms"] == pytest.approx(420.0)


def test_step_timed_out_event_dict() -> None:
    ev = StepTimedOutEvent(
        suite_id="s1",
        scenario_id="sc1",
        step_id="wait_intent",
        timeout_ms=10000,
    )
    d = ev.as_ws_message()
    assert d["type"] == "StepTimedOut"
    assert d["timeout_ms"] == 10000
