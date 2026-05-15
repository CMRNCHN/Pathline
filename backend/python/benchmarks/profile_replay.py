"""Profile the replay seek path.

Loads a synthetic 100-event replay through ``ReplayService.load_replay`` at
ten randomly-chosen offsets and reports per-seek latency along with a
cProfile summary of the heaviest call.

Run directly:
    python -m benchmarks.profile_replay

Use ``run()`` to obtain a JSON-serializable result dict for aggregation by
``baseline_report``. No application code is touched.
"""
from __future__ import annotations

import random
import tempfile
import time
from pathlib import Path
from typing import Any

from ivr_assessor.events.replay_service import ReplayService
from ivr_assessor.events.snapshot_service import SnapshotService

from ._fixtures import ensure_synthetic_session
from ._harness import profile, summarize


REPLAY_SEEK_THRESHOLD_MS = 200.0
EVENT_STREAM_LOAD_THRESHOLD_MS = 200.0


def run(seed: int = 1234) -> dict[str, Any]:
    """Execute the replay-seek benchmark suite.

    Returns a JSON-serializable record with per-seek samples, percentile
    summary, threshold flags, and a cProfile snapshot of one full seek.
    """
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory(prefix="ivr_bench_replay_") as tmp:
        events_dir = Path(tmp) / "events"
        snapshots_dir = Path(tmp) / "snapshots"
        events_dir.mkdir()
        snapshots_dir.mkdir()

        session_id = "bench_replay_100"
        event_count = 100
        ensure_synthetic_session(events_dir, session_id, event_count)

        service = ReplayService(events_dir=events_dir)
        service.snapshot_service = SnapshotService(snapshots_dir=snapshots_dir)

        offsets = [rng.randint(0, event_count) for _ in range(10)]

        # Per-seek wall-clock timings
        seek_samples_ms: list[float] = []
        for offset in offsets:
            start = time.perf_counter()
            service.load_replay(session_id, offset=offset)
            seek_samples_ms.append((time.perf_counter() - start) * 1000.0)

        # Full-replay event stream load (raw JSONL parse via get_raw_events)
        stream_samples_ms: list[float] = []
        for _ in range(5):
            start = time.perf_counter()
            service.get_raw_events(session_id)
            stream_samples_ms.append((time.perf_counter() - start) * 1000.0)

        # cProfile a representative seek so we know where time goes
        deepest_offset = max(offsets) if offsets else event_count
        profile_record = profile(
            lambda: service.load_replay(session_id, offset=deepest_offset),
            name=f"replay_seek(offset={deepest_offset})",
        )

    seek_summary = summarize(seek_samples_ms)
    stream_summary = summarize(stream_samples_ms)

    return {
        "operation": "replay_seek",
        "event_count": event_count,
        "offsets": offsets,
        "samples_ms": [round(v, 3) for v in seek_samples_ms],
        "summary": seek_summary,
        "threshold_ms": REPLAY_SEEK_THRESHOLD_MS,
        "exceeds_threshold": seek_summary["p95_ms"] > REPLAY_SEEK_THRESHOLD_MS,
        "stream_load": {
            "samples_ms": [round(v, 3) for v in stream_samples_ms],
            "summary": stream_summary,
            "threshold_ms": EVENT_STREAM_LOAD_THRESHOLD_MS,
            "exceeds_threshold": (
                stream_summary["p95_ms"] > EVENT_STREAM_LOAD_THRESHOLD_MS
            ),
        },
        "profile": profile_record,
    }


def main() -> None:
    record = run()
    print(f"replay_seek  p50={record['summary']['p50_ms']}ms  "
          f"p95={record['summary']['p95_ms']}ms  "
          f"p99={record['summary']['p99_ms']}ms")
    flag = " WARN" if record["exceeds_threshold"] else " OK"
    print(f"  threshold={record['threshold_ms']}ms{flag}")
    print(f"  total calls profiled: {record['profile']['calls']}")
    for entry in record["profile"]["top_functions"][:5]:
        print(
            f"    {entry['function']}  cum={entry['cumulative_ms']}ms "
            f"tot={entry['total_ms']}ms n={entry['ncalls']}"
        )


if __name__ == "__main__":
    main()
