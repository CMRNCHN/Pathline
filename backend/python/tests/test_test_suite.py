import json
import tempfile
from pathlib import Path

import pytest

from ivr_assessor.live_map import RecordingTelephonyClient
from ivr_assessor.test_suite import (
    TestCase,
    TestCaseResult,
    TestSuiteResult,
    TestTrigger,
    run_test_case,
    run_test_suite_from_file,
    save_suite_result,
)


def test_test_trigger_validation():
    """Valid triggers should be created."""
    t = TestTrigger(phrase="account", response="1234", kind="dtmf")
    assert t.phrase == "account"
    assert t.kind == "dtmf"

    with pytest.raises(ValueError, match="Invalid trigger kind"):
        TestTrigger(phrase="account", response="1234", kind="invalid")


def test_test_case_creation():
    """TestCase should accept triggers and initial path."""
    triggers = [
        TestTrigger(phrase="account number", response="5551234567", kind="dtmf"),
        TestTrigger(phrase="zip code", response="90210", kind="dtmf"),
    ]
    case = TestCase(
        name="Pay bill",
        target_number="+18005550199",
        initial_path=["1", "3"],
        triggers=triggers,
    )
    assert case.name == "Pay bill"
    assert len(case.triggers) == 2
    assert case.initial_path == ["1", "3"]


def test_run_test_case_basic():
    """Running a test case should return a result with transcript and triggers."""
    triggers = [
        TestTrigger(phrase="account number", response="12345", kind="dtmf"),
    ]
    case = TestCase(
        name="Simple test",
        target_number="+18005550199",
        triggers=triggers,
    )
    runner = RecordingTelephonyClient()
    result = run_test_case(case, runner=runner)

    assert result.name == "Simple test"
    assert result.target_number == "+18005550199"
    assert result.session_id.startswith("session-")
    assert len(result.transcript) > 0
    assert result.duration_ms >= 0


def test_run_test_case_fires_triggers():
    """Triggers should fire when phrases match prompts."""
    triggers = [
        TestTrigger(phrase="Welcome", response="1", kind="dtmf"),
    ]
    case = TestCase(
        name="Trigger test",
        target_number="+18005550199",
        triggers=triggers,
    )
    runner = RecordingTelephonyClient()
    result = run_test_case(case, runner=runner)

    # The simulated prompts include "Welcome to billing...", so trigger should fire
    assert len(result.fired_triggers) > 0
    assert result.fired_triggers[0]["phrase"] == "Welcome"


def test_run_test_case_no_match():
    """When triggers don't match, they shouldn't fire."""
    triggers = [
        TestTrigger(phrase="NONEXISTENT_PHRASE_12345", response="1", kind="dtmf"),
    ]
    case = TestCase(
        name="No match test",
        target_number="+18005550199",
        triggers=triggers,
    )
    runner = RecordingTelephonyClient()
    result = run_test_case(case, runner=runner)

    # Trigger shouldn't fire since the phrase doesn't appear in simulated prompts
    assert len(result.fired_triggers) == 0
    assert result.success is False


def test_run_test_suite_from_file():
    """Loading and running a suite from JSON should work."""
    suite_data = {
        "name": "Test Suite",
        "target_number": "+18005550199",
        "cases": [
            {
                "name": "Case 1",
                "target_number": "+18005550199",
                "initial_path": [],
                "triggers": [
                    {"phrase": "account", "response": "1", "kind": "dtmf"}
                ],
            },
            {
                "name": "Case 2",
                "target_number": "+18005550200",
                "initial_path": ["2"],
                "triggers": [
                    {"phrase": "zip", "response": "90210", "kind": "dtmf"}
                ],
            },
        ],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(suite_data, f)
        suite_path = f.name

    try:
        result = run_test_suite_from_file(suite_path)
        assert result.suite_name == "Test Suite"
        assert result.total_cases == 2
        assert len(result.results) == 2
    finally:
        Path(suite_path).unlink()


def test_save_suite_result():
    """Saving a result should create JSON and Markdown files."""
    case_result = TestCaseResult(
        name="Test 1",
        target_number="+18005550199",
        session_id="session-1",
        transcript=[{"kind": "prompt", "text": "Hello", "t_ms": 100}],
        fired_triggers=[],
        final_node="menu-1",
        duration_ms=1000,
        success=True,
    )
    suite_result = TestSuiteResult(
        suite_name="test_suite",
        created_at="2024-01-01T00:00:00",
        total_cases=1,
        passed_cases=1,
        results=[case_result],
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path, md_path = save_suite_result(suite_result, output_dir=tmpdir)
        assert json_path.exists()
        assert md_path.exists()
        assert json_path.suffix == ".json"
        assert md_path.suffix == ".md"

        # Verify JSON content
        with open(json_path) as f:
            data = json.load(f)
            assert data["suite_name"] == "test_suite"
            assert data["total_cases"] == 1

        # Verify Markdown content
        md_content = md_path.read_text()
        assert "Test Suite: test_suite" in md_content
        assert "Passed: 1/1" in md_content


def test_test_case_result_as_dict():
    """TestCaseResult should serialize to dict."""
    result = TestCaseResult(
        name="Test",
        target_number="+18005550199",
        session_id="session-1",
        transcript=[],
        fired_triggers=[],
        final_node=None,
        duration_ms=0,
        success=True,
    )
    d = result.as_dict()
    assert d["name"] == "Test"
    assert d["target_number"] == "+18005550199"
