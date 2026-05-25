from pathlib import Path

import pytest

from replay.inspection_models import NextStep, ReplayInspectionReport


def test_empty_report_json_matches_snapshot_fixture() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "replay_inspection_empty_report.json"

    report = ReplayInspectionReport.empty()

    assert report.to_json() == fixture.read_text(encoding="utf-8")


def test_next_step_requires_non_empty_cites() -> None:
    with pytest.raises(ValueError, match="NextStep.cites must be non-empty"):
        NextStep(action="inspect chronology", rationale="needs grounding", cites=[])
