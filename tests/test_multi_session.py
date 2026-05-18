from runtime.state.models import CallEvent
from runtime.multi_session import MultiSessionOrchestrator


def test_multi_session_combines_graphs_without_cross_talk() -> None:
    orchestrator = MultiSessionOrchestrator()
    orchestrator.start_session("s1", target_number="+15555550100")
    orchestrator.start_session("s2", target_number="+15555550101")

    orchestrator.record_event(
        "s1",
        CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0),
        branch_confidence=0.8,
    )
    orchestrator.record_event(
        "s1",
        CallEvent(kind="action", text="dtmf:1", t_ms=120),
        branch_confidence=0.8,
    )
    orchestrator.record_event(
        "s1",
        CallEvent(kind="prompt", text="Billing menu", t_ms=240),
        branch_confidence=0.7,
    )

    orchestrator.record_event(
        "s2",
        CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0),
        branch_confidence=0.9,
    )
    orchestrator.record_event(
        "s2",
        CallEvent(kind="action", text="dtmf:1", t_ms=100),
        branch_confidence=0.9,
    )
    orchestrator.record_event(
        "s2",
        CallEvent(kind="prompt", text="Sales menu", t_ms=220),
        branch_confidence=0.6,
    )

    combined = orchestrator.combined_graph()
    sessions = orchestrator.session_index()

    assert combined["Press 1 for billing"]["sessions"] == ["s1", "s2"]
    assert combined["Press 1 for billing"]["branches"]["1"]["count"] == 2
    assert combined["Press 1 for billing"]["branches"]["1"]["next_prompts"] == [
        "Billing menu",
        "Sales menu",
    ]

    assert sessions["s1"]["target_number"] == "+15555550100"
    assert sessions["s2"]["target_number"] == "+15555550101"
    assert sessions["s1"]["event_count"] == 3
    assert sessions["s2"]["event_count"] == 3
    assert sessions["s1"]["graph"]["Press 1 for billing"]["branches"]["1"][
        "next_prompts"
    ] == ["Billing menu"]
    assert sessions["s2"]["graph"]["Press 1 for billing"]["branches"]["1"][
        "next_prompts"
    ] == ["Sales menu"]


def test_multi_session_keeps_independent_session_state() -> None:
    orchestrator = MultiSessionOrchestrator()
    orchestrator.start_session("alpha")
    orchestrator.start_session("beta")

    orchestrator.record_event(
        "alpha",
        CallEvent(kind="prompt", text="Press 2 for support", t_ms=0),
        branch_confidence=0.8,
    )
    orchestrator.record_event(
        "alpha",
        CallEvent(kind="action", text="dtmf:2", t_ms=75),
        branch_confidence=0.8,
    )
    orchestrator.record_event(
        "beta",
        CallEvent(kind="prompt", text="Press 2 for support", t_ms=0),
        branch_confidence=0.8,
    )

    sessions = orchestrator.session_index()
    combined = orchestrator.combined_graph()

    assert sessions["alpha"]["graph"]["Press 2 for support"]["branches"]["2"][
        "count"
    ] == 1
    assert sessions["beta"]["graph"]["Press 2 for support"]["branches"] == {}
    assert combined["Press 2 for support"]["sessions"] == ["alpha", "beta"]