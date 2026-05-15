"""Profile export generation (JSON / Mermaid / Markdown).

Three export pathways are measured:

* ``json``    — round-trip a ``ReplayState`` through ``as_dict`` + ``json.dumps``.
* ``mermaid`` — ``map_store.export_mermaid`` on a generated IVR graph.
* ``markdown`` — ``map_store.export_markdown`` on the same graph.

We deliberately bypass ``map_store.save_map`` to avoid touching the user
home directory. The benchmark only renders strings; it never writes maps.
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from ivr_assessor.events.replay_loader import ReplayLoader
from ivr_assessor.events.replay_reducer import apply_event
from ivr_assessor.events.replay_state import ReplayState
from ivr_assessor.ivr_mapper import IvrMapper
from ivr_assessor.map_store import export_markdown, export_mermaid
from ivr_assessor.models import CallEvent

from ._fixtures import (
    build_synthetic_events,
    ensure_synthetic_session,
    load_call_event_trace,
)
from ._harness import profile, summarize


EXPORT_THRESHOLD_MS = 500.0


def _build_replay_state(events_dir: Path) -> ReplayState:
    """Materialise a ReplayState with a moderately rich graph."""
    session_id = "bench_export"
    path = ensure_synthetic_session(events_dir, session_id, event_count=120)
    loader = ReplayLoader(path)
    state = ReplayState(session_id=session_id)
    for event in loader.get_timeline():
        state = apply_event(state, event)
    return state


def _build_mapper_graph() -> dict[str, Any]:
    """Produce a believable IVR graph using the same synthetic event stream.

    Falls back to the bundled ``sample_ivr_trace.json`` if the synthetic
    generator yields nothing (defensive — shouldn't happen).
    """
    mapper = IvrMapper()

    # Prefer the bundled CallEvent trace if it exists; otherwise synthesise
    # a longer one so the graph has multiple branches.
    raw_events = load_call_event_trace()
    if raw_events:
        for item in raw_events:
            mapper.observe(
                CallEvent(
                    kind=str(item["kind"]),
                    text=str(item["text"]),
                    t_ms=int(item["t_ms"]),
                ),
                branch_confidence=0.8,
                session_id="bench-1",
            )

    # Augment with synthetic prompts/actions so the export has real volume.
    synthetic = build_synthetic_events("bench_export_map", event_count=60)
    for ev in synthetic:
        payload = ev.get("payload", {})
        if ev["type"].startswith("TRANSCRIPT") and payload.get("text"):
            mapper.observe(
                CallEvent(kind="prompt", text=payload["text"], t_ms=0),
                branch_confidence=0.75,
                session_id="bench-2",
            )
        elif ev["type"] == "DTMF_SENT" and payload.get("digits"):
            mapper.observe(
                CallEvent(kind="action", text=f"dtmf:{payload['digits']}", t_ms=0),
                branch_confidence=0.75,
                session_id="bench-2",
            )

    return mapper.graph()


def run() -> dict[str, Any]:
    """Execute the export benchmark suite."""
    with tempfile.TemporaryDirectory(prefix="ivr_bench_export_") as tmp:
        events_dir = Path(tmp) / "events"
        events_dir.mkdir()

        state = _build_replay_state(events_dir)
        graph = _build_mapper_graph()

        # Warm import paths to keep first-call noise out of the samples.
        json.dumps(state.as_dict())
        export_mermaid(graph)
        export_markdown(graph)

        json_samples: list[float] = []
        mermaid_samples: list[float] = []
        markdown_samples: list[float] = []

        iterations = 25
        for _ in range(iterations):
            start = time.perf_counter()
            json.dumps(state.as_dict())
            json_samples.append((time.perf_counter() - start) * 1000.0)

            start = time.perf_counter()
            export_mermaid(graph, target="+15555550100")
            mermaid_samples.append((time.perf_counter() - start) * 1000.0)

            start = time.perf_counter()
            export_markdown(graph, target="+15555550100")
            markdown_samples.append((time.perf_counter() - start) * 1000.0)

        json_profile = profile(
            lambda: json.dumps(state.as_dict()),
            name="export_json",
        )
        mermaid_profile = profile(
            lambda: export_mermaid(graph, target="+15555550100"),
            name="export_mermaid",
        )
        markdown_profile = profile(
            lambda: export_markdown(graph, target="+15555550100"),
            name="export_markdown",
        )

    def pack(name: str, samples: list[float], profile_record: dict[str, Any]):
        summary = summarize(samples)
        return {
            "operation": name,
            "iterations": iterations,
            "samples_ms": [round(v, 3) for v in samples],
            "summary": summary,
            "threshold_ms": EXPORT_THRESHOLD_MS,
            "exceeds_threshold": summary["p95_ms"] > EXPORT_THRESHOLD_MS,
            "profile": profile_record,
        }

    return {
        "operation": "export",
        "node_count": len(graph),
        "event_count_in_state": len(state.events),
        "json": pack("export_json", json_samples, json_profile),
        "mermaid": pack("export_mermaid", mermaid_samples, mermaid_profile),
        "markdown": pack("export_markdown", markdown_samples, markdown_profile),
        "threshold_ms": EXPORT_THRESHOLD_MS,
    }


def main() -> None:
    record = run()
    print(
        f"export benchmarks  graph_nodes={record['node_count']}  "
        f"events_in_state={record['event_count_in_state']}"
    )
    for kind in ("json", "mermaid", "markdown"):
        bucket = record[kind]
        summary = bucket["summary"]
        flag = " WARN" if bucket["exceeds_threshold"] else " OK"
        print(
            f"  {bucket['operation']:18s}  p50={summary['p50_ms']}ms  "
            f"p95={summary['p95_ms']}ms  p99={summary['p99_ms']}ms  "
            f"threshold={bucket['threshold_ms']}ms{flag}"
        )


if __name__ == "__main__":
    main()
