"""Dataclass models for Run Suites, Scenarios, Steps, and Results."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any

from analyst.telecom.run_suites.status import StepStatus, SuiteRunStatus


class StepAction(str, Enum):
    START_CALL = "start_call"
    WAIT_FOR_PROMPT = "wait_for_prompt"
    WAIT_FOR_PHRASE = "wait_for_phrase"
    SEND_DTMF = "send_dtmf"
    SEND_SPEECH = "send_speech"
    WAIT_FOR_TRANSCRIPT = "wait_for_transcript"
    WAIT_FOR_INTENT = "wait_for_intent"
    WAIT_FOR_NODE = "wait_for_node"
    WAIT_FOR_TRANSFER = "wait_for_transfer"
    CHECK_SECURE_CARD_SAVED = "check_secure_card_saved"
    CHECK_SECURE_CARD_LOOKUP = "check_secure_card_lookup"
    CHECK_SECURE_CARD_DELETED = "check_secure_card_deleted"
    CHECK_NO_RAW_CARD_LOGGED = "check_no_raw_card_logged"
    CHECK_WEBHOOK_CALLED = "check_webhook_called"
    END_CALL = "end_call"


@dataclass
class TestStep:
    """A single step in a test scenario."""
    step_id: str
    action: StepAction
    input_value: str | None = None
    expected_event: str | None = None
    expected_text_contains: str | None = None
    expected_intent: str | None = None
    expected_node_id: str | None = None
    validation_rule: str | None = None
    timeout_s: float = 10.0
    retry_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["action"] = self.action.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestStep":
        action_raw = data.get("action", "")
        try:
            action = StepAction(action_raw)
        except ValueError:
            raise ValueError(f"Unknown step action: {action_raw!r}")
        return cls(
            step_id=str(data.get("step_id", "")),
            action=action,
            input_value=data.get("input_value") or None,
            expected_event=data.get("expected_event") or None,
            expected_text_contains=data.get("expected_text_contains") or None,
            expected_intent=data.get("expected_intent") or None,
            expected_node_id=data.get("expected_node_id") or None,
            validation_rule=data.get("validation_rule") or None,
            timeout_s=float(data.get("timeout_s", data.get("timeout_ms", 10_000)) or 10),
            retry_count=int(data.get("retry_count", 0)),
        )


@dataclass
class TestScenario:
    """A sequence of steps forming a complete IVR test path.

    Steps may be omitted when the parent RunSuite defines base_steps.
    At runtime the runner resolves the final step list by cloning base_steps,
    substituting {{VAR}} placeholders from params, and injecting
    expected_text_contains into the first wait_for_transcript step.
    """
    scenario_id: str
    name: str
    steps: list[TestStep] = field(default_factory=list)
    target_number: str = ""
    # Human-readable label for the IVR outcome this scenario expects (e.g. "APPROVED").
    ivr_status_label: str | None = None
    # Template variable substitutions applied to base_steps (e.g. {"CARD_NUMBER": "4111..."}).
    params: dict[str, str] = field(default_factory=dict)
    # Injected into the first wait_for_transcript step when using base_steps.
    expected_text_contains: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "target_number": self.target_number,
            "steps": [s.as_dict() for s in self.steps],
        }
        if self.ivr_status_label is not None:
            d["ivr_status_label"] = self.ivr_status_label
        if self.params:
            d["params"] = self.params
        if self.expected_text_contains is not None:
            d["expected_text_contains"] = self.expected_text_contains
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestScenario":
        steps_raw = data.get("steps", [])
        if not isinstance(steps_raw, list):
            raise ValueError("Scenario 'steps' must be an array")
        steps = [TestStep.from_dict(s) for s in steps_raw]
        params_raw = data.get("params") or {}
        if not isinstance(params_raw, dict):
            raise ValueError("Scenario 'params' must be an object")
        scenario_id = str(data.get("scenario_id", ""))
        return cls(
            scenario_id=scenario_id,
            name=str(data.get("name") or scenario_id),
            target_number=str(data.get("target_number", "")),
            steps=steps,
            ivr_status_label=data.get("ivr_status_label") or None,
            params={str(k): str(v) for k, v in params_raw.items()},
            expected_text_contains=data.get("expected_text_contains") or None,
        )


@dataclass
class RunSuite:
    """A collection of scenarios forming a complete test suite.

    base_steps defines a shared step template reused across all scenarios that
    have no steps of their own. Template variables ({{VAR}}) in base_steps are
    substituted per-scenario from TestScenario.params at runtime.
    """
    suite_id: str
    name: str
    description: str = ""
    scenarios: list[TestScenario] = field(default_factory=list)
    target_number: str = ""
    base_steps: list[TestStep] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "suite_id": self.suite_id,
            "name": self.name,
            "description": self.description,
            "target_number": self.target_number,
            "scenarios": [s.as_dict() for s in self.scenarios],
        }
        if self.base_steps:
            d["base_steps"] = [s.as_dict() for s in self.base_steps]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunSuite":
        scenarios_raw = data.get("scenarios", [])
        if not isinstance(scenarios_raw, list):
            raise ValueError("Suite 'scenarios' must be an array")
        scenarios = [TestScenario.from_dict(s) for s in scenarios_raw]
        base_steps_raw = data.get("base_steps", [])
        if not isinstance(base_steps_raw, list):
            raise ValueError("Suite 'base_steps' must be an array")
        base_steps = [TestStep.from_dict(s) for s in base_steps_raw]
        return cls(
            suite_id=str(data.get("suite_id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            target_number=str(data.get("target_number", "")),
            scenarios=scenarios,
            base_steps=base_steps,
        )


# ─── Runtime Result Types ─────────────────────────────────────────────────────

@dataclass
class StepResult:
    """Mutable runtime state for a single step during execution."""
    step_id: str
    action: str
    status: StepStatus = StepStatus.PENDING
    actual_response: str | None = None
    duration_ms: float | None = None
    error: str | None = None
    confidence: float | None = None
    transcript_snippet: str | None = None
    node_id: str | None = None
    secure_card_token: str | None = None
    retry_attempt: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "status": self.status.value,
            "actual_response": self.actual_response,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "confidence": self.confidence,
            "transcript_snippet": self.transcript_snippet,
            "node_id": self.node_id,
            "secure_card_token": self.secure_card_token,
            "retry_attempt": self.retry_attempt,
        }


@dataclass
class ScenarioResult:
    """Aggregated result of one scenario execution."""
    scenario_id: str
    name: str
    step_results: list[StepResult] = field(default_factory=list)
    passed: bool = False
    duration_ms: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    # Set after run: the IVR status label matched (or "UNMATCHED: <transcript>").
    ivr_status: str | None = None
    # Full concatenated transcript captured during this scenario.
    full_transcript: str | None = None

    @property
    def pass_count(self) -> int:
        return sum(1 for s in self.step_results if s.status == StepStatus.PASSED)

    @property
    def fail_count(self) -> int:
        return sum(1 for s in self.step_results
                   if s.status in (StepStatus.FAILED, StepStatus.ERRORED, StepStatus.TIMED_OUT))

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "passed": self.passed,
            "duration_ms": self.duration_ms,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "ivr_status": self.ivr_status,
            "full_transcript": self.full_transcript,
            "step_results": [s.as_dict() for s in self.step_results],
        }


@dataclass
class RunResult:
    """Complete result of a suite run."""
    suite_id: str
    run_id: str
    name: str
    status: SuiteRunStatus = SuiteRunStatus.IDLE
    started_at: float = 0.0
    completed_at: float = 0.0
    scenario_results: list[ScenarioResult] = field(default_factory=list)
    transcript_log: list[dict[str, Any]] = field(default_factory=list)
    event_log: list[dict[str, Any]] = field(default_factory=list)
    secure_card_audit: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at) * 1000
        return 0.0

    @property
    def pass_count(self) -> int:
        return sum(s.pass_count for s in self.scenario_results)

    @property
    def fail_count(self) -> int:
        return sum(s.fail_count for s in self.scenario_results)

    @property
    def timeout_count(self) -> int:
        return sum(
            1 for sc in self.scenario_results
            for st in sc.step_results
            if st.status == StepStatus.TIMED_OUT
        )

    @property
    def failed_steps(self) -> list[dict[str, Any]]:
        out = []
        for sc in self.scenario_results:
            for st in sc.step_results:
                if st.status in (StepStatus.FAILED, StepStatus.ERRORED, StepStatus.TIMED_OUT):
                    out.append({
                        "scenario_id": sc.scenario_id,
                        "scenario_name": sc.name,
                        **st.as_dict(),
                    })
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "run_id": self.run_id,
            "name": self.name,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "timeout_count": self.timeout_count,
            "failed_steps": self.failed_steps,
            "secure_card_audit": self.secure_card_audit,
            "scenario_results": [s.as_dict() for s in self.scenario_results],
        }