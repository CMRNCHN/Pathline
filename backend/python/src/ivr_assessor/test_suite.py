from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .live_map import (
    LiveMappingSession,
    PromptSource,
    RecordingTelephonyClient,
    ScriptedPromptSource,
    build_default_response_library,
)
from .models import CallEvent
from .telephony import TelephonyClient

# Prevent pytest from attempting to collect dataclasses in this runtime module
# as test classes due to their `Test*` names.
__test__ = False


@dataclass(frozen=True)
class TestTrigger:
    phrase: str
    response: str
    kind: str  # "dtmf" or "speech"
    title: str = ""  # human label, e.g. "Account Number"

    def __post_init__(self):
        if self.kind not in ("dtmf", "speech"):
            raise ValueError(f"Invalid trigger kind: {self.kind}")


@dataclass(frozen=True)
class TestCase:
    name: str
    target_number: str
    initial_path: list[str] = field(default_factory=list)
    triggers: list[TestTrigger] = field(default_factory=list)


@dataclass(frozen=True)
class FiredTrigger:
    trigger_index: int
    phrase: str
    t_ms: int
    response: str
    kind: str


@dataclass(frozen=True)
class TestCaseResult:
    name: str
    target_number: str
    session_id: str
    transcript: list[dict[str, object]]
    fired_triggers: list[dict[str, object]]
    final_node: str | None
    duration_ms: int
    success: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TestSuiteResult:
    suite_name: str
    created_at: str
    total_cases: int
    passed_cases: int
    results: list[TestCaseResult]

    def as_dict(self) -> dict[str, object]:
        return {
            "suite_name": self.suite_name,
            "created_at": self.created_at,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "results": [r.as_dict() for r in self.results],
        }

    def as_markdown(self) -> str:
        lines = [
            f"# Test Suite: {self.suite_name}",
            f"Generated: {self.created_at}",
            f"Passed: {self.passed_cases}/{self.total_cases}",
            "",
        ]
        for r in self.results:
            status = "✅" if r.success else "❌"
            lines.append(f"## {status} {r.name}")
            lines.append(f"- **Target:** {r.target_number}")
            lines.append(f"- **Session:** {r.session_id}")
            lines.append(f"- **Duration:** {r.duration_ms}ms")
            lines.append(f"- **Prompts:** {len([e for e in r.transcript if e['kind'] == 'prompt'])}")
            lines.append(f"- **Triggers fired:** {len(r.fired_triggers)}")
            if r.final_node:
                lines.append(f"- **Final node:** {r.final_node}")
            if r.fired_triggers:
                lines.append("- **Trigger timeline:**")
                for ft in r.fired_triggers:
                    lines.append(
                        f"  - [{ft['t_ms']}ms] {ft['phrase']} → {ft['kind']} {ft['response']}"
                    )
            lines.append("")
        return "\n".join(lines)


def validate_suite_payload(payload: object) -> dict[str, object]:
    """Validate and normalize a suite payload loaded from JSON/UI.

    Returns a normalized dict with `name`, `target_number`, and `cases`.
    Raises ValueError with user-friendly messages on invalid input.
    """
    if not isinstance(payload, dict):
        raise ValueError("Suite payload must be a JSON object")

    suite_name = str(payload.get("name", "")).strip() or "untitled-suite"
    default_target = str(payload.get("target_number", "")).strip()
    cases_raw = payload.get("cases", [])

    if not isinstance(cases_raw, list):
        raise ValueError("Suite 'cases' must be a JSON array")
    if not cases_raw:
        raise ValueError("Suite must include at least one test case")

    normalized_cases: list[dict[str, object]] = []
    for idx, item in enumerate(cases_raw):
        if not isinstance(item, dict):
            raise ValueError(f"Case #{idx + 1} must be an object")

        case_name = str(item.get("name", "")).strip() or f"case-{idx + 1}"
        target_number = str(item.get("target_number", default_target)).strip()
        if not target_number:
            raise ValueError(
                f"Case '{case_name}' is missing target_number (and no suite default provided)"
            )

        initial_path_raw = item.get("initial_path", [])
        if not isinstance(initial_path_raw, list):
            raise ValueError(f"Case '{case_name}' initial_path must be an array")
        initial_path = [str(step).strip() for step in initial_path_raw if str(step).strip()]

        triggers_raw = item.get("triggers", [])
        if not isinstance(triggers_raw, list):
            raise ValueError(f"Case '{case_name}' triggers must be an array")

        normalized_triggers: list[dict[str, str]] = []
        for t_idx, trigger in enumerate(triggers_raw):
            if not isinstance(trigger, dict):
                raise ValueError(
                    f"Case '{case_name}' trigger #{t_idx + 1} must be an object"
                )
            phrase = str(trigger.get("phrase", "")).strip()
            response = str(trigger.get("response", "")).strip()
            kind = str(trigger.get("kind", "dtmf")).strip() or "dtmf"

            if not phrase:
                raise ValueError(f"Case '{case_name}' has a trigger with empty phrase")
            if not response:
                raise ValueError(f"Case '{case_name}' has a trigger with empty response")
            if kind not in ("dtmf", "speech"):
                raise ValueError(
                    f"Case '{case_name}' trigger '{phrase}' has invalid kind '{kind}'"
                )

            title = str(trigger.get("title", "")).strip()
            entry: dict[str, str] = {"phrase": phrase, "response": response, "kind": kind}
            if title:
                entry["title"] = title
            normalized_triggers.append(entry)

        normalized_cases.append(
            {
                "name": case_name,
                "target_number": target_number,
                "initial_path": initial_path,
                "triggers": normalized_triggers,
            }
        )

    variables_raw = payload.get("variables", {})
    variables = {str(k): str(v) for k, v in variables_raw.items()} if isinstance(variables_raw, dict) else {}

    return {
        "name": suite_name,
        "target_number": default_target,
        "variables": variables,
        "cases": normalized_cases,
    }


class _TestInterceptor(PromptSource):
    """Wraps a prompt source to fire triggers and initial path digits."""

    def __init__(
        self,
        source: PromptSource,
        triggers: list[TestTrigger],
        initial_path: list[str],
        telephony: TelephonyClient,
        session: LiveMappingSession,
    ):
        self.source = source
        self.triggers = triggers
        self.initial_path = list(initial_path)
        self.telephony = telephony
        self.session = session
        self.fired_triggers: list[FiredTrigger] = []
        self.fired_indices: set[int] = set()
        self._initial_path_injected = False

    def next_event(self, session_id: str) -> CallEvent | None:
        # Send initial path immediately on first event poll
        if not self._initial_path_injected:
            self._initial_path_injected = True
            for i, digit in enumerate(self.initial_path):
                self.telephony.send_dtmf(session_id, digit)
                evt = CallEvent(kind="action", text=f"dtmf:{digit}", t_ms=(i + 1) * 100)
                self.session._record_event(evt, branch_confidence=1.0)

        event = self.source.next_event(session_id)
        if event and event.kind == "prompt":
            text_lower = event.text.lower()
            for idx, trigger in enumerate(self.triggers):
                if idx in self.fired_indices:
                    continue
                if trigger.phrase.lower() in text_lower:
                    if trigger.kind == "dtmf":
                        self.telephony.send_dtmf(session_id, trigger.response)
                        action_text = f"dtmf:{trigger.response}"
                    else:
                        self.telephony.say(session_id, trigger.response)
                        action_text = f"say:{trigger.response}"

                    self.fired_triggers.append(
                        FiredTrigger(
                            trigger_index=idx,
                            phrase=trigger.phrase,
                            t_ms=event.t_ms,
                            response=trigger.response,
                            kind=trigger.kind,
                        )
                    )
                    self.fired_indices.add(idx)

                    # Record the action directly into the session ledger
                    evt = CallEvent(kind="action", text=action_text, t_ms=event.t_ms + 10)
                    self.session._record_event(evt, branch_confidence=1.0)

        return event


def run_test_case(
    test_case: TestCase,
    runner: TelephonyClient | None = None,
    prompt_source: PromptSource | None = None,
) -> TestCaseResult:
    client = runner or RecordingTelephonyClient()

    source = prompt_source or ScriptedPromptSource([
        CallEvent(kind="prompt", text="Welcome to billing. Press 1 for account info.", t_ms=1000),
        CallEvent(kind="prompt", text="Please enter your account number.", t_ms=2000),
        CallEvent(kind="prompt", text="Thank you. Your account is confirmed.", t_ms=3000),
    ])

    session = LiveMappingSession(
        target_number=test_case.target_number,
        response_mode="mixed",
        prompt_source=source,
        telephony=client,
        response_library=build_default_response_library("general"),
        manual_mode=True,  # Prevent auto-exploration; test runner drives actions
    )

    interceptor = _TestInterceptor(
        source=source,
        triggers=test_case.triggers,
        initial_path=test_case.initial_path,
        telephony=client,
        session=session,
    )
    session.prompt_source = interceptor

    summary = session.run()

    graph = summary.graph
    final_node = list(graph.keys())[-1] if graph else None
    transcript = [asdict(e) for e in session.ledger.all()]

    duration_ms = (
        transcript[-1]["t_ms"] - transcript[0]["t_ms"]
        if transcript
        else 0
    )
    success = len(interceptor.fired_triggers) == len(test_case.triggers)

    return TestCaseResult(
        name=test_case.name,
        target_number=test_case.target_number,
        session_id=summary.session_id,
        transcript=transcript,
        fired_triggers=[asdict(ft) for ft in interceptor.fired_triggers],
        final_node=final_node,
        duration_ms=duration_ms,
        success=success,
    )


def run_test_suite_from_file(
    suite_path: str | Path,
    runner: TelephonyClient | None = None,
) -> TestSuiteResult:
    path = Path(suite_path)
    if not path.exists():
        raise FileNotFoundError(f"Test suite file not found: {path}")

    with open(path) as f:
        payload = json.load(f)

    normalized = validate_suite_payload(payload)
    suite_name = str(normalized.get("name", path.stem))
    cases_data = normalized.get("cases", [])

    # Build variable substitution map from suite-level `variables` dict.
    # Values referenced as $variable_name in trigger responses are replaced here.
    variables: dict[str, str] = {
        str(k): str(v)
        for k, v in (payload.get("variables") or {}).items()
        if k and v is not None
    }

    def _interpolate(text: str) -> str:
        for k, v in variables.items():
            text = text.replace(f"${k}", v)
        return text

    test_cases = []
    for item in cases_data:
        triggers = [
            TestTrigger(
                phrase=t["phrase"],
                response=_interpolate(t["response"]),
                kind=t.get("kind", "dtmf"),
                title=t.get("title", ""),
            )
            for t in item.get("triggers", [])
        ]
        case = TestCase(
            name=item.get("name", f"case-{len(test_cases)}"),
            target_number=item.get("target_number", normalized.get("target_number", "")),
            initial_path=item.get("initial_path", []),
            triggers=triggers,
        )
        test_cases.append(case)

    results = []
    for case in test_cases:
        result = run_test_case(case, runner=runner)
        results.append(result)

    passed = sum(1 for r in results if r.success)
    created_at = datetime.now().isoformat()

    return TestSuiteResult(
        suite_name=suite_name,
        created_at=created_at,
        total_cases=len(results),
        passed_cases=passed,
        results=results,
    )


def save_suite_result(
    result: TestSuiteResult,
    output_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    """Save test suite result to JSON and Markdown.

    Returns: (json_path, markdown_path)
    """
    if output_dir is None:
        output_dir = Path.home() / ".ivr_assessor" / "reports"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Create suite-specific directory
    suite_dir = output_dir / result.suite_name.replace(" ", "_").lower()
    suite_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = suite_dir / f"result-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(json_path, "w") as f:
        json.dump(result.as_dict(), f, indent=2)

    # Save Markdown summary
    md_path = suite_dir / f"result-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    with open(md_path, "w") as f:
        f.write(result.as_markdown())

    return json_path, md_path
