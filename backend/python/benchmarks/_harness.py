"""Reusable measurement harness for IVR Assessor benchmarks.

Wraps the standard-library cProfile + pstats around callables, returning a
JSON-serializable dict with wall-clock duration, total call count, and the
top hot functions. Designed for offline baseline measurement; never imported
by production code.

Usage:
    from benchmarks._harness import profile, percentile, format_ms

    record = profile(lambda: do_work(), name="my_op")
    # record["duration_ms"], record["calls"], record["top_functions"]

The harness intentionally avoids any third-party dependency.
"""
from __future__ import annotations

import cProfile
import io
import pstats
import statistics
import time
from typing import Any, Callable


def profile(
    func: Callable[[], Any],
    name: str,
    top_n: int = 10,
) -> dict[str, Any]:
    """Profile a zero-argument callable and return a JSON-serializable record.

    Parameters
    ----------
    func:
        Zero-argument callable. The return value (if any) is discarded;
        wrap arguments via ``functools.partial`` or a closure.
    name:
        Human-readable identifier recorded on the result.
    top_n:
        How many of the heaviest functions to capture.

    Returns
    -------
    dict with keys:
        - name: str
        - duration_ms: float (wall-clock)
        - calls: int (total profiled function calls)
        - top_functions: list[dict] with keys
            {function, cumulative_ms, total_ms, ncalls}
    """
    profiler = cProfile.Profile()
    start = time.perf_counter()
    profiler.enable()
    try:
        func()
    finally:
        profiler.disable()
    duration_ms = (time.perf_counter() - start) * 1000.0

    stats = pstats.Stats(profiler)
    stats.sort_stats(pstats.SortKey.CUMULATIVE)

    top_functions: list[dict[str, Any]] = []
    # stats.stats: dict[(file, line, name)] -> (cc, nc, tt, ct, callers)
    entries = sorted(
        stats.stats.items(),
        key=lambda item: item[1][3],  # cumulative time
        reverse=True,
    )[:top_n]

    for (file_path, lineno, fname), (_cc, nc, tt, ct, _callers) in entries:
        top_functions.append(
            {
                "function": f"{_short_path(file_path)}:{lineno}:{fname}",
                "cumulative_ms": round(ct * 1000.0, 3),
                "total_ms": round(tt * 1000.0, 3),
                "ncalls": nc,
            }
        )

    total_calls = sum(entry[1][1] for entry in stats.stats.items())

    return {
        "name": name,
        "duration_ms": round(duration_ms, 3),
        "calls": total_calls,
        "top_functions": top_functions,
    }


def percentile(values: list[float], pct: float) -> float:
    """Compute a percentile from a list of floats (linear interpolation).

    Returns 0.0 for an empty list rather than raising; benchmark output
    happily prints zeros where samples are missing.
    """
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(values)
    # statistics.quantiles uses method "exclusive" by default; we want the
    # NIST-style inclusive linear interpolation for percentile reporting.
    k = (len(ordered) - 1) * (pct / 100.0)
    lower = int(k)
    upper = min(lower + 1, len(ordered) - 1)
    frac = k - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * frac


def summarize(samples: list[float]) -> dict[str, float]:
    """Reduce a list of per-iteration ms measurements to a stats dict."""
    if not samples:
        return {
            "count": 0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "mean_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
        }
    return {
        "count": len(samples),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
        "mean_ms": round(statistics.fmean(samples), 3),
        "p50_ms": round(percentile(samples, 50), 3),
        "p95_ms": round(percentile(samples, 95), 3),
        "p99_ms": round(percentile(samples, 99), 3),
    }


def format_ms(value: float) -> str:
    return f"{value:.2f} ms"


def _short_path(path: str) -> str:
    """Trim absolute paths to a readable suffix for the report."""
    marker = "ivr_assessor"
    idx = path.find(marker)
    if idx >= 0:
        return path[idx:]
    # Keep last two path components otherwise
    parts = path.replace("\\", "/").split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else path


def collect_profile_summary(profile_record: dict[str, Any]) -> io.StringIO:
    """Render a profile record as a small text block (for ad-hoc CLI use)."""
    buf = io.StringIO()
    buf.write(f"{profile_record['name']}\n")
    buf.write(f"  duration: {profile_record['duration_ms']} ms\n")
    buf.write(f"  total calls: {profile_record['calls']}\n")
    buf.write("  top functions:\n")
    for entry in profile_record["top_functions"][:5]:
        buf.write(
            f"    {entry['function']}  cum={entry['cumulative_ms']}ms "
            f"tot={entry['total_ms']}ms n={entry['ncalls']}\n"
        )
    return buf
