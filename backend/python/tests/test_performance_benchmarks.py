"""Smoke tests for the performance benchmark suite.

These tests confirm that every profile module runs end-to-end and emits a
non-empty, JSON-serializable record. They intentionally do **not** assert
on latency — the benchmarks publish baseline measurements, not constraints.

The benchmark modules live in ``backend/python/benchmarks/``. A separate
``benchmarks`` package exists at the repo root (for ``wer_benchmark``), so
we import via ``importlib.util`` against the file paths directly. That
keeps ``sys.modules['benchmarks']`` untouched and avoids interfering with
other tests that depend on the repo-root package.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

BENCHMARK_DIR = Path(__file__).resolve().parents[1] / "benchmarks"


def _load(module_name: str) -> ModuleType:
    """Load a benchmark module by file path, registered under a sandbox name.

    We prefix every module with ``_ivr_perf_bench_`` so it cannot collide
    with the unrelated ``benchmarks`` package at the repo root.
    """
    sandbox_name = f"_ivr_perf_bench_{module_name}"
    if sandbox_name in sys.modules:
        return sys.modules[sandbox_name]

    # Ensure helper siblings (_harness, _fixtures) resolve when the module
    # we are loading uses relative imports like ``from ._harness import …``.
    package_name = "_ivr_perf_bench_pkg"
    if package_name not in sys.modules:
        pkg_spec = importlib.util.spec_from_file_location(
            package_name,
            BENCHMARK_DIR / "__init__.py",
            submodule_search_locations=[str(BENCHMARK_DIR)],
        )
        assert pkg_spec is not None and pkg_spec.loader is not None
        pkg_module = importlib.util.module_from_spec(pkg_spec)
        sys.modules[package_name] = pkg_module
        pkg_spec.loader.exec_module(pkg_module)

    full_name = f"{package_name}.{module_name}"
    spec = importlib.util.spec_from_file_location(
        full_name,
        BENCHMARK_DIR / f"{module_name}.py",
        submodule_search_locations=None,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    sys.modules[sandbox_name] = module
    spec.loader.exec_module(module)
    return module


def _assert_summary_shape(summary: dict) -> None:
    for key in ("count", "min_ms", "max_ms", "mean_ms", "p50_ms", "p95_ms", "p99_ms"):
        assert key in summary, f"missing key {key} in summary"


def test_replay_benchmark_runs() -> None:
    profile_replay = _load("profile_replay")
    record = profile_replay.run()
    assert record["operation"] == "replay_seek"
    assert record["event_count"] == 100
    assert record["summary"]["count"] == 10
    _assert_summary_shape(record["summary"])
    _assert_summary_shape(record["stream_load"]["summary"])
    # cProfile must capture at least one frame
    assert record["profile"]["calls"] > 0
    # Round-trip through JSON to confirm full serializability
    json.dumps(record)


def test_snapshot_benchmark_runs() -> None:
    profile_snapshots = _load("profile_snapshots")
    record = profile_snapshots.run()
    # If fixtures vanished entirely, the run() may report skipped — still
    # JSON-serialisable and the smoke test passes.
    json.dumps(record)
    if record.get("skipped"):
        return
    assert record["operation"] == "snapshot_load"
    assert record["sessions"] >= 1
    _assert_summary_shape(record["load"]["summary"])
    _assert_summary_shape(record["create"]["summary"])
    _assert_summary_shape(record["persist"]["summary"])
    assert record["profile"]["calls"] > 0


def test_export_benchmark_runs() -> None:
    profile_exports = _load("profile_exports")
    record = profile_exports.run()
    assert record["operation"] == "export"
    assert record["node_count"] >= 1
    for kind in ("json", "mermaid", "markdown"):
        bucket = record[kind]
        _assert_summary_shape(bucket["summary"])
        assert bucket["iterations"] >= 1
        assert bucket["profile"]["calls"] > 0
    json.dumps(record)
