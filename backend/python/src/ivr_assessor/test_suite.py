from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

from .ivr_mapper import IvrMapper
from .live_map import RecordingTelephonyClient
from .models import CallEvent
from .telephony import TelephonyClient


@dataclass(frozen=True)
class TestTrigger:
    phrase: str
    response: str
    kind: str  # "dtmf" or "speech"

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


def run_test_case(
    test_case: TestCase,
    runner: TelephonyClient | None = None,
) -> TestCaseResult:
    client = runner or RecordingTelephonyClient()
    session_id = client.dial(test_case.target_number)
    mapper = IvrMapper()
    transcript: list[dict[str, object]] = []
    fired_triggers: list[FiredTrigger] = []
    t_start = 0
    final_node: str | None = None

    # Inject initial path as DTMF
    for i, digit in enumerate(test_case.initial_path):
        client.send_dtmf(session_id, digit)
        t_ms = (i + 1) * 100
        transcript.append({"kind": "action", "text": f"dtmf:{digit}", "t_ms": t_ms})

    # Simulate call progression with transcript events
    # In a real scenario, these would come from Deepgram/Twilio
    # For now, we'll process a dummy transcript and fire triggers based on it
    simulated_events = [
        CallEvent(kind="prompt", text="Welcome to billing. Press 1 for account info.", t_ms=1000),
        CallEvent(kind="prompt", text="Please enter your account number.", t_ms=2000),
        CallEvent(kind="prompt", text="Thank you. Your account is confirmed.", t_ms=3000),
    ]

    for event in simulated_events:
        transcript.append({"kind": event.kind, "text": event.text, "t_ms": event.t_ms})
        mapper.observe(event, branch_confidence=0.9, session_id=session_id)

        # Check for trigger matches in this prompt
        if event.kind == "prompt":
            for idx, trigger in enumerate(test_case.triggers):
                if trigger.phrase.lower() in event.text.lower():
                    # Fire the trigger
                    if trigger.kind == "dtmf":
                        client.send_dtmf(session_id, trigger.response)
                    elif trigger.kind == "speech":
                        client.say(session_id, trigger.response)

                    fired = FiredTrigger(
                        trigger_index=idx,
                        phrase=trigger.phrase,
                        t_ms=event.t_ms,
                        response=trigger.response,
                        kind=trigger.kind,
                    )
                    fired_triggers.append(fired)
                    transcript.append(
                        {
                            "kind": "action",
                            "text": f"{trigger.kind}:{trigger.response}",
                            "t_ms": event.t_ms + 10,
                        }
                    )

    client.hangup(session_id)

    # Get final node from mapper
    graph = mapper.graph()
    if graph:
        final_node = list(graph.keys())[-1] if graph else None

    duration_ms = (
        transcript[-1]["t_ms"] - transcript[0]["t_ms"]
        if transcript
        else 0
    )
    success = len(fired_triggers) == len(test_case.triggers)

    return TestCaseResult(
        name=test_case.name,
        target_number=test_case.target_number,
        session_id=session_id,
        transcript=transcript,
        fired_triggers=[asdict(ft) for ft in fired_triggers],
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

    suite_name = payload.get("name", path.stem)
    cases_data = payload.get("cases", [])

    test_cases = []
    for item in cases_data:
        triggers = [
            TestTrigger(
                phrase=t["phrase"],
                response=t["response"],
                kind=t.get("kind", "dtmf"),
            )
            for t in item.get("triggers", [])
        ]
        case = TestCase(
            name=item.get("name", f"case-{len(test_cases)}"),
            target_number=item.get("target_number", payload.get("target_number", "")),
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
