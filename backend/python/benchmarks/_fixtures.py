"""Fixture helpers for benchmark suites.

We need realistic, repeatable event streams without depending on captured
production data. These builders generate deterministic synthetic sessions
covering the CALL_STARTED → NODE/EDGE_DISCOVERED → DTMF_SENT →
PATH_ADVANCED → CALL_COMPLETED lifecycle handled by ``replay_reducer``.

The builders also know how to honour ``tests/fixtures/`` when real fixtures
exist; otherwise they fall back to the synthetic generator. Benchmarks call
``ensure_synthetic_session`` to materialise a JSONL file in a tmp directory
and ``ensure_snapshot_set`` to write a few session JSON blobs for snapshot
load benchmarks.
"""
from __future__ import annotations

import json
from pathlib import Path

from ivr_assessor.events.event_types import EventType

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"


def build_synthetic_events(
    session_id: str,
    *,
    event_count: int,
    base_ts: float = 1_700_000_000.0,
) -> list[dict]:
    """Return ``event_count`` events that exercise every reducer branch.

    The sequence is:
        1 × CALL_STARTED
        repeated cycles of:
            NODE_DISCOVERED, EDGE_DISCOVERED, TRANSCRIPT_FINAL,
            DTMF_SENT, PATH_ADVANCED
        1 × CALL_COMPLETED at the end
    All timestamps are monotonically increasing in 50 ms steps.
    """
    if event_count < 2:
        event_count = 2

    events: list[dict] = []
    ts = base_ts

    def push(event_type: str, payload: dict) -> None:
        nonlocal ts
        ts += 0.05
        events.append(
            {
                "type": event_type,
                "payload": payload,
                "meta": {"timestamp": ts, "session_id": session_id},
            }
        )

    push(EventType.CALL_STARTED, {"call_sid": f"CA{session_id}"})

    cycle = [
        (
            EventType.NODE_DISCOVERED,
            lambda i: {"id": f"N{i}", "label": f"Prompt {i}"},
        ),
        (
            EventType.EDGE_DISCOVERED,
            lambda i: {"from": f"N{i - 1}" if i > 0 else "ROOT", "to": f"N{i}"},
        ),
        (
            EventType.TRANSCRIPT_FINAL,
            lambda i: {
                "text": f"prompt {i} for the caller",
                "speaker": "system",
                "speech_start_offset": 0.1 * i,
            },
        ),
        (EventType.DTMF_SENT, lambda i: {"digits": str((i % 9) + 1)}),
        (EventType.PATH_ADVANCED, lambda i: {"node_id": f"N{i}"}),
    ]

    i = 0
    while len(events) < event_count - 1:
        event_type, payload_factory = cycle[len(events) % len(cycle)]
        push(event_type, payload_factory(i))
        if event_type == EventType.PATH_ADVANCED:
            i += 1

    push(EventType.CALL_COMPLETED, {})
    return events[:event_count]


def write_session_jsonl(events: list[dict], events_dir: Path, session_id: str) -> Path:
    """Persist events to ``events_dir/<date>/session_<id>.jsonl`` and return path.

    The ``<date>`` directory follows the same ``YYYY-MM-DD`` convention used
    in production so ``ReplayService`` can discover the file.
    """
    date_str = "2026-05-15"
    target_dir = events_dir / date_str
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"session_{session_id}.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")
    return path


def ensure_synthetic_session(
    events_dir: Path,
    session_id: str,
    event_count: int,
) -> Path:
    """Create a synthetic session file if missing and return its path."""
    return write_session_jsonl(
        build_synthetic_events(session_id, event_count=event_count),
        events_dir,
        session_id,
    )


def ensure_snapshot_set(
    events_dir: Path,
    *,
    count: int = 5,
    event_count: int = 80,
) -> list[Path]:
    """Build ``count`` distinct session JSONL files for snapshot reconstruction.

    Each session has ``event_count`` events. The returned paths can be fed to
    ``ReplayService.load_replay`` for snapshot-reconstruction benchmarks.
    """
    paths: list[Path] = []
    for idx in range(count):
        sid = f"bench_snap_{idx:02d}"
        paths.append(ensure_synthetic_session(events_dir, sid, event_count))
    return paths


def load_call_event_trace() -> list[dict]:
    """Read the bundled ``sample_ivr_trace.json`` (CallEvent list).

    Returns an empty list if the fixture is missing — caller benchmarks
    must skip gracefully.
    """
    path = FIXTURE_DIR / "sample_ivr_trace.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
