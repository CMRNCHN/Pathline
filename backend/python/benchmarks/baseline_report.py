"""Aggregate baseline benchmark runner.

Runs every profile module in this package and emits two artefacts:

* ``backend/python/docs/performance_baseline.json``
  — Machine-readable record of every measurement (P50 / P95 / P99,
  per-sample timings, cProfile top functions).

* ``backend/python/docs/PERFORMANCE_BASELINE.md``
  — Human-readable Markdown summary table with threshold flags.

Run with:

    python -m benchmarks.baseline_report

This module is **measurement-only** — it never modifies application code,
adds dependencies, or alters runtime configuration.
"""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import profile_exports, profile_replay, profile_snapshots


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
JSON_REPORT = DOCS_DIR / "performance_baseline.json"
MD_REPORT = DOCS_DIR / "PERFORMANCE_BASELINE.md"

WARN = "WARN"
OK = "OK"


def _flatten_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten nested benchmark results into a row list for the Markdown table."""
    rows: list[dict[str, Any]] = []

    # ── Replay seek ────────────────────────────────────────────────────────
    replay = results["replay"]
    rows.append(
        {
            "operation": "replay_seek (100-event session)",
            "summary": replay["summary"],
            "threshold_ms": replay["threshold_ms"],
            "exceeds": replay["exceeds_threshold"],
            "notes": (
                f"{replay['event_count']} events, "
                f"{replay['summary']['count']} seeks"
            ),
        }
    )
    stream = replay["stream_load"]
    rows.append(
        {
            "operation": "event_stream_load (raw JSONL)",
            "summary": stream["summary"],
            "threshold_ms": stream["threshold_ms"],
            "exceeds": stream["exceeds_threshold"],
            "notes": f"{replay['event_count']} events, "
                     f"{stream['summary']['count']} iterations",
        }
    )

    # ── Snapshot load ──────────────────────────────────────────────────────
    snap = results["snapshots"]
    if snap.get("skipped"):
        rows.append(
            {
                "operation": "snapshot_load",
                "summary": {
                    "p50_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                    "mean_ms": 0.0,
                    "count": 0,
                },
                "threshold_ms": profile_snapshots.SNAPSHOT_LOAD_THRESHOLD_MS,
                "exceeds": False,
                "notes": f"skipped: {snap.get('reason', 'unknown')}",
            }
        )
    else:
        rows.append(
            {
                "operation": "snapshot_load (5 sessions)",
                "summary": snap["load"]["summary"],
                "threshold_ms": snap["load"]["threshold_ms"],
                "exceeds": snap["load"]["exceeds_threshold"],
                "notes": f"{snap['sessions']} sessions reconstructed",
            }
        )
        rows.append(
            {
                "operation": "snapshot_create",
                "summary": snap["create"]["summary"],
                "threshold_ms": snap["load"]["threshold_ms"],
                "exceeds": False,
                "notes": "in-memory copy of ReplayState",
            }
        )
        rows.append(
            {
                "operation": "snapshot_persist (json dump)",
                "summary": snap["persist"]["summary"],
                "threshold_ms": snap["load"]["threshold_ms"],
                "exceeds": False,
                "notes": "indented JSON to tmp disk",
            }
        )

    # ── Exports ────────────────────────────────────────────────────────────
    exports = results["exports"]
    for kind in ("json", "mermaid", "markdown"):
        bucket = exports[kind]
        rows.append(
            {
                "operation": bucket["operation"],
                "summary": bucket["summary"],
                "threshold_ms": bucket["threshold_ms"],
                "exceeds": bucket["exceeds_threshold"],
                "notes": (
                    f"graph_nodes={exports['node_count']}, "
                    f"iters={bucket['iterations']}"
                ),
            }
        )

    return rows


def _render_markdown(results: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    meta = results["meta"]
    lines: list[str] = []
    lines.append("# Performance Baseline")
    lines.append("")
    lines.append(
        "Baseline measurements captured by `benchmarks/baseline_report.py`. "
        "These numbers describe **current** behaviour; they are *not* "
        "performance constraints. Use them as the reference point when "
        "evaluating future optimisation work."
    )
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append(f"- Captured at: `{meta['captured_at']}`")
    lines.append(f"- Python: `{meta['python']}`")
    lines.append(f"- Platform: `{meta['platform']}`")
    lines.append("")
    lines.append("## Target Thresholds")
    lines.append("")
    lines.append("| Operation | Threshold |")
    lines.append("| --- | --- |")
    lines.append(
        f"| replay_seek | < {profile_replay.REPLAY_SEEK_THRESHOLD_MS:.0f} ms (P95) |"
    )
    lines.append(
        f"| event_stream_load | < "
        f"{profile_replay.EVENT_STREAM_LOAD_THRESHOLD_MS:.0f} ms (P95) |"
    )
    lines.append(
        f"| snapshot_load | < "
        f"{profile_snapshots.SNAPSHOT_LOAD_THRESHOLD_MS:.0f} ms (P95) |"
    )
    lines.append(
        f"| export_* | < {profile_exports.EXPORT_THRESHOLD_MS:.0f} ms (P95) |"
    )
    lines.append("")
    lines.append("## Measurements")
    lines.append("")
    lines.append(
        "| Operation | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) | "
        "Samples | Threshold (ms) | Status | Notes |"
    )
    lines.append(
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: | --- |"
    )

    flagged: list[str] = []
    for row in rows:
        summary = row["summary"]
        status = WARN if row["exceeds"] else OK
        if row["exceeds"]:
            flagged.append(row["operation"])
        lines.append(
            "| {op} | {p50:.2f} | {p95:.2f} | {p99:.2f} | {mean:.2f} | "
            "{count} | {threshold:.0f} | {status} | {notes} |".format(
                op=row["operation"],
                p50=summary["p50_ms"],
                p95=summary["p95_ms"],
                p99=summary["p99_ms"],
                mean=summary["mean_ms"],
                count=summary["count"],
                threshold=row["threshold_ms"],
                status=status,
                notes=row["notes"],
            )
        )

    lines.append("")
    lines.append("## Threshold Violations")
    lines.append("")
    if flagged:
        lines.append("The following operations exceeded their P95 threshold:")
        lines.append("")
        for op in flagged:
            lines.append(f"- {op}")
    else:
        lines.append("None — every measured P95 is within target.")
    lines.append("")

    lines.append("## Hot Functions (cProfile, cumulative time)")
    lines.append("")
    lines.append(
        "Snapshots of the heaviest call sites from one representative run "
        "of each profiled operation. Cumulative time is wall-clock time "
        "spent in the function *including* callees."
    )
    lines.append("")

    profile_buckets: list[tuple[str, dict[str, Any]]] = [
        ("replay_seek", results["replay"].get("profile") or {}),
    ]
    if not results["snapshots"].get("skipped"):
        profile_buckets.append(
            ("snapshot_load", results["snapshots"].get("profile") or {})
        )
    profile_buckets.append(
        ("export_json", results["exports"]["json"]["profile"])
    )
    profile_buckets.append(
        ("export_mermaid", results["exports"]["mermaid"]["profile"])
    )
    profile_buckets.append(
        ("export_markdown", results["exports"]["markdown"]["profile"])
    )

    for label, prof in profile_buckets:
        if not prof:
            continue
        lines.append(f"### {label}")
        lines.append("")
        lines.append(
            f"- duration: {prof.get('duration_ms', 0):.2f} ms, "
            f"calls: {prof.get('calls', 0)}"
        )
        lines.append("")
        lines.append("| Function | Cumulative (ms) | Total (ms) | Calls |")
        lines.append("| --- | ---: | ---: | ---: |")
        for entry in prof.get("top_functions", [])[:8]:
            lines.append(
                "| `{fn}` | {cum:.2f} | {tot:.2f} | {n} |".format(
                    fn=entry["function"],
                    cum=entry["cumulative_ms"],
                    tot=entry["total_ms"],
                    n=entry["ncalls"],
                )
            )
        lines.append("")

    lines.append("## Reproducing")
    lines.append("")
    lines.append("```sh")
    lines.append("cd backend/python")
    lines.append("python -m benchmarks.baseline_report")
    lines.append("```")
    lines.append("")
    lines.append(
        "Individual modules — `benchmarks.profile_replay`, "
        "`benchmarks.profile_snapshots`, `benchmarks.profile_exports` — can be "
        "run directly for ad-hoc investigation."
    )
    lines.append("")

    return "\n".join(lines)


def collect() -> dict[str, Any]:
    """Run every benchmark and return the aggregated record."""
    return {
        "meta": {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "replay": profile_replay.run(),
        "snapshots": profile_snapshots.run(),
        "exports": profile_exports.run(),
    }


def write_reports(results: dict[str, Any]) -> tuple[Path, Path]:
    """Persist JSON + Markdown reports under ``backend/python/docs/``."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    rows = _flatten_rows(results)

    JSON_REPORT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    MD_REPORT.write_text(_render_markdown(results, rows), encoding="utf-8")
    return JSON_REPORT, MD_REPORT


def main() -> None:
    results = collect()
    json_path, md_path = write_reports(results)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")

    rows = _flatten_rows(results)
    flagged = [r["operation"] for r in rows if r["exceeds"]]
    if flagged:
        print("Threshold violations:")
        for op in flagged:
            print(f"  - {op}")
    else:
        print("All measured P95 latencies within target thresholds.")


if __name__ == "__main__":
    main()
