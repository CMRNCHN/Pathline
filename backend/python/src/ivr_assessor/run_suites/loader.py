"""Load, validate, save, import, and export Run Suite JSON files."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import RunSuite, TestScenario, TestStep, StepAction

_SUITE_DIR = Path.home() / ".ivr_assessor" / "run_suites"

# Allowed characters in suite_id / scenario_id / step_id
_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


def _validate_suite_dict(data: Any) -> None:
    """Raise ValueError with a clear message if the suite JSON is malformed."""
    if not isinstance(data, dict):
        raise ValueError("Suite JSON must be an object")

    suite_id = data.get("suite_id", "")
    if not suite_id:
        raise ValueError("Suite is missing 'suite_id'")
    if not _ID_RE.match(str(suite_id)):
        raise ValueError(f"Invalid suite_id {suite_id!r} — use letters, digits, _ or - only")

    if not data.get("name"):
        raise ValueError("Suite is missing 'name'")

    scenarios_raw = data.get("scenarios")
    if not isinstance(scenarios_raw, list):
        raise ValueError("Suite 'scenarios' must be an array")
    if not scenarios_raw:
        raise ValueError("Suite must contain at least one scenario")

    valid_actions = {a.value for a in StepAction}
    for si, sc in enumerate(scenarios_raw):
        if not isinstance(sc, dict):
            raise ValueError(f"Scenario #{si + 1} must be an object")

        sc_id = sc.get("scenario_id", "")
        if not sc_id:
            raise ValueError(f"Scenario #{si + 1} is missing 'scenario_id'")
        if not _ID_RE.match(str(sc_id)):
            raise ValueError(f"Invalid scenario_id {sc_id!r}")

        if not sc.get("name"):
            raise ValueError(f"Scenario {sc_id!r} is missing 'name'")

        steps_raw = sc.get("steps")
        if not isinstance(steps_raw, list):
            raise ValueError(f"Scenario {sc_id!r} 'steps' must be an array")
        if not steps_raw:
            raise ValueError(f"Scenario {sc_id!r} must contain at least one step")

        seen_step_ids: set[str] = set()
        for ti, step in enumerate(steps_raw):
            if not isinstance(step, dict):
                raise ValueError(f"Scenario {sc_id!r} step #{ti + 1} must be an object")

            step_id = step.get("step_id", "")
            if not step_id:
                raise ValueError(f"Step #{ti + 1} in scenario {sc_id!r} missing 'step_id'")
            if step_id in seen_step_ids:
                raise ValueError(
                    f"Duplicate step_id {step_id!r} in scenario {sc_id!r}"
                )
            seen_step_ids.add(step_id)

            action = step.get("action", "")
            if action not in valid_actions:
                raise ValueError(
                    f"Step {step_id!r} has unknown action {action!r}. "
                    f"Valid actions: {sorted(valid_actions)}"
                )

            timeout_ms = step.get("timeout_ms", 10_000)
            if not isinstance(timeout_ms, (int, float)) or timeout_ms <= 0:
                raise ValueError(
                    f"Step {step_id!r} timeout_ms must be a positive number"
                )

            # Actions that require input_value
            if action in ("send_dtmf", "send_speech") and not step.get("input_value"):
                raise ValueError(
                    f"Step {step_id!r} action {action!r} requires 'input_value'"
                )


def load_suite(suite_id: str, suites_dir: Path | None = None) -> RunSuite:
    """Load a RunSuite from disk by suite_id."""
    directory = suites_dir or _SUITE_DIR
    path = directory / f"{suite_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Run suite not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    _validate_suite_dict(data)
    return RunSuite.from_dict(data)


def save_suite(suite: RunSuite, suites_dir: Path | None = None) -> Path:
    """Persist a RunSuite to disk. Returns the saved file path."""
    directory = suites_dir or _SUITE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{suite.suite_id}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(suite.as_dict(), f, indent=2)
    return path


def delete_suite(suite_id: str, suites_dir: Path | None = None) -> None:
    """Delete a suite file from disk."""
    directory = suites_dir or _SUITE_DIR
    path = directory / f"{suite_id}.json"
    if path.exists():
        path.unlink()


def list_suites(suites_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return a list of suite metadata dicts from all saved suites."""
    directory = suites_dir or _SUITE_DIR
    if not directory.exists():
        return []
    out = []
    for p in sorted(directory.glob("*.json")):
        try:
            with p.open(encoding="utf-8") as f:
                data = json.load(f)
            out.append({
                "suite_id": data.get("suite_id", p.stem),
                "name": data.get("name", p.stem),
                "description": data.get("description", ""),
                "scenario_count": len(data.get("scenarios", [])),
                "filename": p.name,
            })
        except Exception:
            pass
    return out


def import_suite_json(raw_json: str) -> RunSuite:
    """Parse and validate a suite from a raw JSON string (e.g. from UI paste)."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc
    _validate_suite_dict(data)
    return RunSuite.from_dict(data)


def export_suite_json(suite: RunSuite, indent: int = 2) -> str:
    """Serialize a RunSuite to a JSON string."""
    return json.dumps(suite.as_dict(), indent=indent)
