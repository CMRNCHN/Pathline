from pathlib import Path

from replay.inspection_models import ReplayInspectionReport


def test_empty_report_json_matches_snapshot_fixture() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "replay_inspection_empty_report.json"

    report = ReplayInspectionReport.empty()

    assert report.to_json() == fixture.read_text(encoding="utf-8")
