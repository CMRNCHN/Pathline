from runtime.ivr_mapper import IvrMapper
from runtime.state.models import CallEvent


def test_mapper_builds_graph_across_events() -> None:
    mapper = IvrMapper()

    mapper.observe(
        CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0),
        branch_confidence=0.8,
        session_id="s1",
    )
    mapper.observe(
        CallEvent(kind="action", text="dtmf:1", t_ms=200),
        branch_confidence=0.8,
        session_id="s1",
    )
    mapper.observe(
        CallEvent(kind="prompt", text="Billing menu", t_ms=350),
        branch_confidence=0.7,
        session_id="s1",
    )

    graph = mapper.graph()

    assert "Press 1 for billing" in graph
    assert graph["Press 1 for billing"]["sessions"] == ["s1"]
    assert graph["Press 1 for billing"]["observations"] == 1
    assert graph["Press 1 for billing"]["branches"]["1"]["count"] == 1
    assert graph["Press 1 for billing"]["branches"]["1"]["next_prompts"] == [
        "Billing menu"
    ]


def test_mapper_refines_graph_across_sessions() -> None:
    mapper = IvrMapper()

    mapper.observe(
        CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0),
        branch_confidence=0.8,
        session_id="s1",
    )
    mapper.observe(
        CallEvent(kind="action", text="dtmf:1", t_ms=100),
        branch_confidence=0.8,
        session_id="s1",
    )
    mapper.observe(
        CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0),
        branch_confidence=0.9,
        session_id="s2",
    )
    mapper.observe(
        CallEvent(kind="action", text="dtmf:1", t_ms=100),
        branch_confidence=0.9,
        session_id="s2",
    )

    graph = mapper.graph()
    node = graph["Press 1 for billing"]

    assert node["sessions"] == ["s1", "s2"]
    assert node["observations"] == 2
    assert node["branches"]["1"]["count"] == 2