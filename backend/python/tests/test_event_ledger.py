from ivr_assessor.event_ledger import EventLedger
from ivr_assessor.models import CallEvent, CallPlan


def test_call_plan_defaults_allowed_branches_to_isolated_empty_list() -> None:
    plan = CallPlan(
        target_number="+15551234567",
        max_depth=4,
        max_attempts=2,
        dtmf_timeout_ms=1500,
        response_mode="scripted",
        exploration_budget=3,
        confidence_threshold=0.75,
    )

    assert plan.allowed_branches == []
    plan.allowed_branches.append("billing")
    assert CallPlan(
        target_number="+15551234567",
        max_depth=4,
        max_attempts=2,
        dtmf_timeout_ms=1500,
        response_mode="scripted",
        exploration_budget=3,
        confidence_threshold=0.75,
    ).allowed_branches == []


def test_event_ledger_records_in_order_and_returns_copy() -> None:
    ledger = EventLedger()
    first = CallEvent(kind="prompt", text="Welcome", t_ms=100)
    second = CallEvent(kind="dtmf", text="1", t_ms=250)

    ledger.record(first)
    ledger.record(second)

    recorded = ledger.all()

    assert recorded == [first, second]
    assert recorded is not ledger.all()
    recorded.append(CallEvent(kind="system", text="mutated", t_ms=999))
    assert ledger.all() == [first, second]
