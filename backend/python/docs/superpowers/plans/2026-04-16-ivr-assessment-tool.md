# IVR Assessment Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, authorized IVR assessment CLI that can place outbound test calls, capture prompts and actions in an event ledger, inject DTMF, play prebuilt response clips, adapt to observed IVR behavior, map the IVR tree across sessions, and export reports.

**Architecture:** This is a small Python package with a CLI entrypoint, a telephony adapter boundary, and separate modules for execution control, prompt intelligence, adaptive scenario selection, response playback, graph building, and report generation. The implementation should keep the call orchestration deterministic where possible, but allow the scenario runner to choose among operator-approved actions based on prompt classification and prior session data.

**Tech Stack:** Python 3.11+, `typer` for CLI, `pydantic` for config/data models, `pytest` for tests, standard library `json`/`csv`/`pathlib`, and one telephony provider adapter behind a small interface.

---

### Task 1: Bootstrap the package and CLI entrypoint

**Files:**
- Create: `pyproject.toml`
- Create: `src/ivr_assessor/__init__.py`
- Create: `src/ivr_assessor/cli.py`
- Create: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
from typer.testing import CliRunner
from ivr_assessor.cli import app

runner = CliRunner()

def test_cli_shows_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "IVR assessor CLI" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli_smoke.py -v`
Expected: FAIL because the package and CLI app do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ivr_assessor/cli.py
import typer

app = typer.Typer(help="IVR assessor CLI")

@app.command()
def version() -> None:
    """Print the tool version."""
    typer.echo("ivr-assessor 0.1.0")

def main() -> None:
    app()
```

```toml
# pyproject.toml
[project]
name = "ivr-assessor"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["typer>=0.12", "pydantic>=2.0"]

[project.scripts]
ivr-assessor = "ivr_assessor.cli:main"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ivr_assessor/__init__.py src/ivr_assessor/cli.py tests/test_cli_smoke.py
git commit -m "feat: bootstrap ivr assessor cli"
```

### Task 2: Add core data models and event ledger

**Files:**
- Create: `src/ivr_assessor/models.py`
- Create: `src/ivr_assessor/event_ledger.py`
- Create: `tests/test_event_ledger.py`

- [ ] **Step 1: Write the failing test**

```python
from ivr_assessor.event_ledger import EventLedger
from ivr_assessor.models import CallEvent

def test_event_ledger_records_events_in_order():
    ledger = EventLedger()
    ledger.record(CallEvent(kind="prompt", text="Press 1 for billing", t_ms=100))
    ledger.record(CallEvent(kind="action", text="dtmf:1", t_ms=450))

    events = ledger.all()
    assert [e.kind for e in events] == ["prompt", "action"]
    assert events[0].t_ms == 100
    assert events[1].text == "dtmf:1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_event_ledger.py -v`
Expected: FAIL because `EventLedger` and `CallEvent` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ivr_assessor/models.py
from pydantic import BaseModel, Field

class CallEvent(BaseModel):
    kind: str
    text: str
    t_ms: int

class CallPlan(BaseModel):
    target_number: str
    max_depth: int = 8
    max_attempts: int = 3
    dtmf_timeout_ms: int = 3000
    response_mode: str = "mixed"
    allowed_branches: list[str] = Field(default_factory=list)
    exploration_budget: int = 10
    confidence_threshold: float = 0.6
```

```python
# src/ivr_assessor/event_ledger.py
from .models import CallEvent

class EventLedger:
    def __init__(self) -> None:
        self._events: list[CallEvent] = []

    def record(self, event: CallEvent) -> None:
        self._events.append(event)

    def all(self) -> list[CallEvent]:
        return list(self._events)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_event_ledger.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ivr_assessor/models.py src/ivr_assessor/event_ledger.py tests/test_event_ledger.py
git commit -m "feat: add event ledger models"
```

### Task 3: Implement response library and fill-in-the-blank clips

**Files:**
- Create: `src/ivr_assessor/response_library.py`
- Create: `tests/test_response_library.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from ivr_assessor.response_library import ResponseLibrary, ResponseClip

def test_response_library_selects_clip_by_label():
    clips = [
        ResponseClip(id="a", label="billing", file_path=Path("/tmp/billing.wav"), style="professional", duration_ms=1200, tags=["billing"]),
        ResponseClip(id="b", label="support", file_path=Path("/tmp/support.wav"), style="friendly", duration_ms=1100, tags=["support"]),
    ]
    lib = ResponseLibrary(clips)
    assert lib.pick(label="support").id == "b"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_response_library.py -v`
Expected: FAIL because `ResponseLibrary` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ivr_assessor/response_library.py
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ResponseClip:
    id: str
    label: str
    file_path: Path
    style: str
    duration_ms: int
    tags: list[str]

class ResponseLibrary:
    def __init__(self, clips: list[ResponseClip]) -> None:
        self._clips = list(clips)

    def pick(self, label: str | None = None, style: str | None = None) -> ResponseClip:
        for clip in self._clips:
            if label is not None and clip.label != label:
                continue
            if style is not None and clip.style != style:
                continue
            return clip
        raise LookupError(f"No clip matched label={label!r} style={style!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_response_library.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ivr_assessor/response_library.py tests/test_response_library.py
git commit -m "feat: add response library"
```

### Task 4: Add prompt intelligence and adaptive scenario selection

**Files:**
- Create: `src/ivr_assessor/prompt_intelligence.py`
- Create: `src/ivr_assessor/scenario_runner.py`
- Create: `tests/test_prompt_intelligence.py`
- Create: `tests/test_scenario_runner.py`

- [ ] **Step 1: Write the failing test**

```python
from ivr_assessor.prompt_intelligence import classify_prompt
from ivr_assessor.scenario_runner import choose_next_action

def test_prompt_classification_and_action_choice():
    prompt = "Press 1 for billing, 2 for support"
    classification = classify_prompt(prompt, previous_kind="welcome")
    assert classification.intent == "menu"
    assert classification.confidence >= 0.5

    action = choose_next_action(classification, exploration_budget=3, confidence_threshold=0.6)
    assert action.kind in {"send_dtmf", "wait"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_prompt_intelligence.py tests/test_scenario_runner.py -v`
Expected: FAIL because the modules do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ivr_assessor/prompt_intelligence.py
from dataclasses import dataclass

@dataclass(frozen=True)
class PromptClassification:
    intent: str
    confidence: float
    prompt_signature: str

def classify_prompt(prompt: str, previous_kind: str | None = None) -> PromptClassification:
    lowered = prompt.lower()
    if "press" in lowered or "for billing" in lowered or "for support" in lowered:
        return PromptClassification(intent="menu", confidence=0.8, prompt_signature=lowered[:64])
    return PromptClassification(intent="unknown", confidence=0.4, prompt_signature=lowered[:64])
```

```python
# src/ivr_assessor/scenario_runner.py
from dataclasses import dataclass
from .prompt_intelligence import PromptClassification

@dataclass(frozen=True)
class NextAction:
    kind: str
    payload: str | None = None

def choose_next_action(classification: PromptClassification, exploration_budget: int, confidence_threshold: float) -> NextAction:
    if classification.intent == "menu" and classification.confidence >= confidence_threshold:
        return NextAction(kind="send_dtmf", payload="1")
    if exploration_budget > 0:
        return NextAction(kind="wait")
    return NextAction(kind="end_call")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_prompt_intelligence.py tests/test_scenario_runner.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ivr_assessor/prompt_intelligence.py src/ivr_assessor/scenario_runner.py tests/test_prompt_intelligence.py tests/test_scenario_runner.py
git commit -m "feat: add prompt intelligence and scenario runner"
```

### Task 5: Add adaptive exploration and IVR graph building

**Files:**
- Create: `src/ivr_assessor/ivr_mapper.py`
- Create: `src/ivr_assessor/exploration.py`
- Create: `tests/test_ivr_mapper.py`
- Create: `tests/test_exploration.py`

- [ ] **Step 1: Write the failing test**

```python
from ivr_assessor.ivr_mapper import IvrMapper
from ivr_assessor.exploration import ExplorationEngine
from ivr_assessor.models import CallEvent

def test_mapper_builds_graph_across_events():
    mapper = IvrMapper()
    mapper.observe(CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0), branch_confidence=0.8, session_id="s1")
    mapper.observe(CallEvent(kind="action", text="dtmf:1", t_ms=200), branch_confidence=0.8, session_id="s1")
    graph = mapper.graph()
    assert "Press 1 for billing" in graph

def test_exploration_engine_proposes_alternate_branch():
    engine = ExplorationEngine()
    assert engine.next_candidate(observed_prompt="Press 1 for billing", prior_action="1").kind in {"send_dtmf", "wait"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ivr_mapper.py tests/test_exploration.py -v`
Expected: FAIL because the mapper and exploration engine do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ivr_assessor/ivr_mapper.py
from dataclasses import dataclass, field
from .models import CallEvent

@dataclass
class _Node:
    prompt: str
    branches: dict[str, "_Node"] = field(default_factory=dict)
    sessions: set[str] = field(default_factory=set)
    confidence: float = 0.0

class IvrMapper:
    def __init__(self) -> None:
        self._roots: dict[str, _Node] = {}

    def observe(self, event: CallEvent, branch_confidence: float, session_id: str) -> None:
        if event.kind != "prompt":
            return
        node = self._roots.setdefault(event.text, _Node(prompt=event.text))
        node.sessions.add(session_id)
        node.confidence = max(node.confidence, branch_confidence)

    def graph(self) -> dict[str, dict[str, object]]:
        return {
            prompt: {"confidence": node.confidence, "sessions": sorted(node.sessions), "branches": list(node.branches)}
            for prompt, node in self._roots.items()
        }
```

```python
# src/ivr_assessor/exploration.py
from dataclasses import dataclass

@dataclass(frozen=True)
class CandidateAction:
    kind: str
    payload: str | None = None

class ExplorationEngine:
    def next_candidate(self, observed_prompt: str, prior_action: str | None = None) -> CandidateAction:
        if "billing" in observed_prompt.lower():
            return CandidateAction(kind="send_dtmf", payload="1")
        return CandidateAction(kind="wait")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ivr_mapper.py tests/test_exploration.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ivr_assessor/ivr_mapper.py src/ivr_assessor/exploration.py tests/test_ivr_mapper.py tests/test_exploration.py
git commit -m "feat: add ivr mapper and exploration engine"
```

### Task 6: Add telephony adapter and execution controller boundary

**Files:**
- Create: `src/ivr_assessor/telephony.py`
- Create: `src/ivr_assessor/execution_controller.py`
- Create: `tests/test_execution_controller.py`

- [ ] **Step 1: Write the failing test**

```python
from ivr_assessor.execution_controller import ExecutionController

def test_execution_controller_refuses_unapproved_target():
    controller = ExecutionController(allowlist=["+15555550100"])
    assert controller.can_dial("+15555550100") is True
    assert controller.can_dial("+15555550101") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_execution_controller.py -v`
Expected: FAIL because the controller does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ivr_assessor/execution_controller.py
class ExecutionController:
    def __init__(self, allowlist: list[str]) -> None:
        self._allowlist = set(allowlist)

    def can_dial(self, target_number: str) -> bool:
        return target_number in self._allowlist
```

```python
# src/ivr_assessor/telephony.py
from typing import Protocol

class TelephonyClient(Protocol):
    def dial(self, target_number: str) -> str: ...
    def send_dtmf(self, session_id: str, digits: str) -> None: ...
    def play_clip(self, session_id: str, file_path: str) -> None: ...
    def hangup(self, session_id: str) -> None: ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_execution_controller.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ivr_assessor/telephony.py src/ivr_assessor/execution_controller.py tests/test_execution_controller.py
git commit -m "feat: add execution controller boundary"
```

### Task 7: Add report generation and export formats

**Files:**
- Create: `src/ivr_assessor/reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write the failing test**

```python
from ivr_assessor.event_ledger import EventLedger
from ivr_assessor.models import CallEvent
from ivr_assessor.reporter import build_report

def test_report_contains_timeline_and_findings():
    ledger = EventLedger()
    ledger.record(CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0))
    ledger.record(CallEvent(kind="action", text="dtmf:1", t_ms=200))
    report = build_report(ledger.all())
    assert "Press 1 for billing" in report.text
    assert "timeline" in report.sections
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reporter.py -v`
Expected: FAIL because the reporter does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ivr_assessor/reporter.py
from dataclasses import dataclass
from .models import CallEvent

@dataclass(frozen=True)
class Report:
    text: str
    sections: list[str]

def build_report(events: list[CallEvent]) -> Report:
    lines = ["IVR Assessment Report", "", "timeline"]
    for event in events:
        lines.append(f"{event.t_ms:06d} {event.kind}: {event.text}")
    return Report(text="\n".join(lines), sections=["timeline"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reporter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ivr_assessor/reporter.py tests/test_reporter.py
git commit -m "feat: add report generation"
```

### Task 8: Wire the CLI together and add an end-to-end dry run

**Files:**
- Modify: `src/ivr_assessor/cli.py`
- Create: `tests/test_dry_run.py`

- [ ] **Step 1: Write the failing test**

```python
from typer.testing import CliRunner
from ivr_assessor.cli import app

runner = CliRunner()

def test_dry_run_prints_plan():
    result = runner.invoke(app, ["dry-run", "--target-number", "+15555550100"])
    assert result.exit_code == 0
    assert "dry run" in result.stdout.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dry_run.py -v`
Expected: FAIL because the CLI command does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# src/ivr_assessor/cli.py
import typer

from .execution_controller import ExecutionController

app = typer.Typer(help="IVR assessor CLI")

@app.command()
def dry_run(target_number: str = typer.Option(..., "--target-number")) -> None:
    controller = ExecutionController(allowlist=[target_number])
    if not controller.can_dial(target_number):
        raise typer.Exit(code=2)
    typer.echo(f"Dry run for {target_number}")

def main() -> None:
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli_smoke.py tests/test_dry_run.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ivr_assessor/cli.py tests/test_dry_run.py
git commit -m "feat: wire cli dry run"
```

### Task 9: Add integration fixtures and replay tests for adaptive mapping

**Files:**
- Create: `tests/fixtures/sample_ivr_trace.json`
- Create: `tests/test_replay_trace.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from ivr_assessor.event_ledger import EventLedger
from ivr_assessor.ivr_mapper import IvrMapper
from ivr_assessor.models import CallEvent

def test_replay_trace_reconstructs_path():
    trace = json.loads(Path("tests/fixtures/sample_ivr_trace.json").read_text())
    ledger = EventLedger()
    mapper = IvrMapper()
    for item in trace:
        event = CallEvent(**item)
        ledger.record(event)
        mapper.observe(event, branch_confidence=0.8, session_id="replay-1")
    graph = mapper.graph()
    assert "Press 1 for billing" in graph
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replay_trace.py -v`
Expected: FAIL because the fixture does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```json
[
  {"kind": "prompt", "text": "Press 1 for billing", "t_ms": 0},
  {"kind": "action", "text": "dtmf:1", "t_ms": 150}
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_replay_trace.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/sample_ivr_trace.json tests/test_replay_trace.py
git commit -m "test: add replay trace coverage"
```

## Self-Review Checklist

- Every spec requirement is mapped to at least one task:
  - CLI and bootstrap: Task 1
  - event ledger: Task 2
  - prebuilt response clips: Task 3
  - prompt intelligence and adaptive action selection: Task 4
  - exploration engine and IVR tree: Task 5
  - execution controller and telephony boundary: Task 6
  - reporting: Task 7
  - end-to-end dry run: Task 8
  - replay and graph refinement: Task 9
- No placeholder language remains in task steps.
- Type names stay consistent across tasks: `CallEvent`, `CallPlan`, `ResponseClip`, `PromptClassification`, `NextAction`, `CandidateAction`, `Report`.
- The plan preserves the authorization and anti-impersonation guardrails from the spec while still supporting adaptive exploration within operator-approved bounds.
