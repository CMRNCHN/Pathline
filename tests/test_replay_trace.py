import json
from pathlib import Path

from runtime.state.event_ledger import EventLedger
from runtime.ivr_mapper import IvrMapper
from runtime.state.models import CallEvent


def test_replay_trace_reconstructs_path() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "sample_ivr_trace.json"
    trace = json.loads(fixture.read_text())
    ledger = EventLedger()
    mapper = IvrMapper()

    for item in trace:
        event = CallEvent(**item)
        ledger.record(event)
        mapper.observe(event, branch_confidence=0.8, session_id="replay-1")

    graph = mapper.graph()

    assert "Press 1 for billing" in graph
    assert graph["Press 1 for billing"]["branches"]["1"]["next_prompts"] == [
        "Billing menu"
    ]