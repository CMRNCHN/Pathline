from ivr_assessor.event_ledger import EventLedger
from ivr_assessor.models import CallEvent
from ivr_assessor.reporter import build_report


def test_report_contains_timeline_and_findings() -> None:
    ledger = EventLedger()
    ledger.record(CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0))
    ledger.record(CallEvent(kind="action", text="dtmf:1", t_ms=200))

    report = build_report(ledger.all())

    assert "Press 1 for billing" in report.text
    assert "timeline" in report.sections
    assert "findings" in report.sections
