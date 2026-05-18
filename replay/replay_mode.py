from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from runtime.state.event_ledger import EventLedger
from runtime.ivr_mapper import IvrMapper
from runtime.state.models import CallEvent
from analyst.reporter import Report, build_report


@dataclass(frozen=True)
class ReplayResult:
    events: list[CallEvent]
    graph: dict[str, dict[str, object]]
    report: Report
    summary: dict[str, object]


def load_trace(trace_path: str | Path) -> list[CallEvent]:
    raw_events = json.loads(Path(trace_path).read_text())
    return parse_events(raw_events)


def parse_events(raw_events: Sequence[Mapping[str, object] | CallEvent]) -> list[CallEvent]:
    events: list[CallEvent] = []
    for item in raw_events:
        if isinstance(item, CallEvent):
            events.append(item)
            continue

        events.append(
            CallEvent(
                kind=str(item["kind"]),
                text=str(item["text"]),
                t_ms=int(item["t_ms"]),
            )
        )
    return events


def replay_trace(trace_source: str | Path | Sequence[Mapping[str, object] | CallEvent]) -> ReplayResult:
    if isinstance(trace_source, (str, Path)):
        events = load_trace(trace_source)
    else:
        events = parse_events(trace_source)

    ledger = EventLedger()
    mapper = IvrMapper()

    for event in events:
        ledger.record(event)
        mapper.observe(event, branch_confidence=0.8, session_id="replay-1")

    replayed_events = ledger.all()
    report = build_report(replayed_events)
    graph = mapper.graph()
    summary = _build_summary(replayed_events, graph)

    return ReplayResult(events=replayed_events, graph=graph, report=report, summary=summary)


def _build_summary(
    events: Sequence[CallEvent],
    graph: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    prompt_count = sum(1 for event in events if event.kind == "prompt")
    action_count = sum(1 for event in events if event.kind == "action")
    return {
        "event_count": len(events),
        "prompt_count": prompt_count,
        "action_count": action_count,
        "node_count": len(graph),
        "root_prompts": sorted(graph),
    }