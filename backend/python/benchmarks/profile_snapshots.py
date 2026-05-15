"""Profile snapshot creation, persistence, and reconstruction.

Builds five synthetic sessions (matching the spec's "5 sample sessions from
tests/fixtures/" requirement — see ``_fixtures.ensure_snapshot_set``), then
measures:

* Snapshot creation from a fully replayed state.
* Snapshot persistence (JSON dump to disk).
* Snapshot load + replay reconstruction round-trip.

If real fixtures appear under ``tests/fixtures/sessions/`` they are picked
up automatically; otherwise the synthetic generator is used.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any

from ivr_assessor.events.replay_loader import ReplayLoader
from ivr_assessor.events.replay_reducer import apply_event
from ivr_assessor.events.replay_service import ReplayService
from ivr_assessor.events.replay_state import ReplayState
from ivr_assessor.events.snapshot_service import SnapshotService

from ._fixtures import FIXTURE_DIR, ensure_snapshot_set
from ._harness import profile, summarize


SNAPSHOT_LOAD_THRESHOLD_MS = 100.0


def _real_fixture_sessions() -> list[Path]:
    """Look for ``tests/fixtures/sessions/*.jsonl`` if a curator added any."""
    sessions_root = FIXTURE_DIR / "sessions"
    if not sessions_root.exists():
        return []
    return sorted(sessions_root.glob("*.jsonl"))


def _replay_state_from_jsonl(path: Path) -> ReplayState:
    loader = ReplayLoader(path)
    events = loader.get_timeline()
    state = ReplayState(session_id=path.stem.replace("session_", ""))
    for event in events:
        state = apply_event(state, event)
    return state


def run() -> dict[str, Any]:
    """Execute the snapshot benchmark suite."""
    create_samples_ms: list[float] = []
    persist_samples_ms: list[float] = []
    load_samples_ms: list[float] = []
    skipped = False

    profile_record: dict[str, Any] | None = None

    with tempfile.TemporaryDirectory(prefix="ivr_bench_snap_") as tmp:
        events_dir = Path(tmp) / "events"
        snapshots_dir = Path(tmp) / "snapshots"
        events_dir.mkdir()
        snapshots_dir.mkdir()

        # Prefer real fixtures when available; otherwise synthesise.
        real_paths = _real_fixture_sessions()
        if real_paths:
            session_paths = real_paths[:5]
        else:
            session_paths = ensure_snapshot_set(
                events_dir, count=5, event_count=80
            )

        if not session_paths:
            skipped = True
            return {
                "operation": "snapshot_load",
                "skipped": True,
                "reason": "no session fixtures available",
            }

        snapshot_service = SnapshotService(snapshots_dir=snapshots_dir)
        replay_service = ReplayService(events_dir=events_dir)
        replay_service.snapshot_service = snapshot_service

        # Phase 1: create + persist snapshots for each session
        for path in session_paths:
            state = _replay_state_from_jsonl(path)
            event_offset = len(state.events)

            start = time.perf_counter()
            snapshot = snapshot_service.create_snapshot(state, event_offset)
            create_samples_ms.append((time.perf_counter() - start) * 1000.0)

            start = time.perf_counter()
            snapshot_service.persist_snapshot(snapshot)
            persist_samples_ms.append((time.perf_counter() - start) * 1000.0)

        # Phase 2: load each persisted snapshot through the replay service
        for path in session_paths:
            session_id = path.stem.replace("session_", "")
            start = time.perf_counter()
            replay_service.load_replay(session_id)
            load_samples_ms.append((time.perf_counter() - start) * 1000.0)

        # cProfile the load path on a representative session
        target_session = session_paths[0].stem.replace("session_", "")
        profile_record = profile(
            lambda: replay_service.load_replay(target_session),
            name=f"snapshot_load({target_session})",
        )

    load_summary = summarize(load_samples_ms)
    return {
        "operation": "snapshot_load",
        "skipped": skipped,
        "sessions": len(load_samples_ms),
        "create": {
            "samples_ms": [round(v, 3) for v in create_samples_ms],
            "summary": summarize(create_samples_ms),
        },
        "persist": {
            "samples_ms": [round(v, 3) for v in persist_samples_ms],
            "summary": summarize(persist_samples_ms),
        },
        "load": {
            "samples_ms": [round(v, 3) for v in load_samples_ms],
            "summary": load_summary,
            "threshold_ms": SNAPSHOT_LOAD_THRESHOLD_MS,
            "exceeds_threshold": load_summary["p95_ms"] > SNAPSHOT_LOAD_THRESHOLD_MS,
        },
        "threshold_ms": SNAPSHOT_LOAD_THRESHOLD_MS,
        "exceeds_threshold": load_summary["p95_ms"] > SNAPSHOT_LOAD_THRESHOLD_MS,
        "profile": profile_record,
    }


def main() -> None:
    record = run()
    if record.get("skipped"):
        print(f"snapshot_load  SKIPPED ({record.get('reason')})")
        return
    summary = record["load"]["summary"]
    flag = " WARN" if record["exceeds_threshold"] else " OK"
    print(
        f"snapshot_load  p50={summary['p50_ms']}ms  "
        f"p95={summary['p95_ms']}ms  p99={summary['p99_ms']}ms  "
        f"threshold={record['threshold_ms']}ms{flag}"
    )
    if record.get("profile"):
        for entry in record["profile"]["top_functions"][:5]:
            print(
                f"    {entry['function']}  cum={entry['cumulative_ms']}ms "
                f"tot={entry['total_ms']}ms n={entry['ncalls']}"
            )


if __name__ == "__main__":
    main()
