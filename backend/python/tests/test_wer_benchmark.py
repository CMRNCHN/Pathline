"""Tests for benchmarks/wer_benchmark.py — metric math only, no real STT."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the benchmarks package importable from the test runner.
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "benchmarks"))
# Adjust to repo root so 'benchmarks' is on the path.
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from benchmarks.wer_benchmark import (  # noqa: E402
    BenchmarkReport,
    FileBenchmarkResult,
    normalize_text,
    word_error_rate,
)


# ─── Text normalization ────────────────────────────────────────────────────────

def test_normalize_lowercases() -> None:
    assert normalize_text("Hello World") == "hello world"


def test_normalize_strips_punctuation() -> None:
    assert normalize_text("press one, please.") == "press one please"


def test_normalize_collapses_whitespace() -> None:
    assert normalize_text("  press   one  ") == "press one"


# ─── WER computation ──────────────────────────────────────────────────────────

def test_wer_perfect_match() -> None:
    assert word_error_rate("press one", "press one") == 0.0


def test_wer_one_substitution_in_two_words() -> None:
    # "hello world" vs "hello there" — 1 sub in 2 words = 0.5
    assert word_error_rate("hello world", "hello there") == pytest.approx(0.5)


def test_wer_empty_hypothesis() -> None:
    # 2 deletions in 2 words = 1.0
    assert word_error_rate("press one", "") == pytest.approx(1.0)


def test_wer_empty_reference_empty_hypothesis() -> None:
    assert word_error_rate("", "") == 0.0


def test_wer_hallucination_above_one() -> None:
    # 3 extra words inserted into a 1-word reference = WER > 1
    wer = word_error_rate("yes", "yes please go ahead now")
    assert wer > 1.0


def test_wer_case_insensitive() -> None:
    assert word_error_rate("Press One", "press one") == 0.0


def test_wer_punctuation_ignored() -> None:
    assert word_error_rate("press one, please.", "press one please") == 0.0


# ─── BenchmarkReport rendering ────────────────────────────────────────────────

def _make_report() -> BenchmarkReport:
    result = FileBenchmarkResult(
        filename="call_001.wav",
        reference="press one",
        hypothesis="press one",
        wer=0.0,
        confidence=0.9,
        latency_ms=350.0,
        hallucination=False,
    )
    return BenchmarkReport(
        backend="faster-whisper",
        model="small.en",
        mean_wer=0.0,
        mean_confidence=0.9,
        mean_latency_ms=350.0,
        results=[result],
    )


def test_report_markdown_contains_backend() -> None:
    md = _make_report().as_markdown()
    assert "faster-whisper" in md


def test_report_markdown_contains_file() -> None:
    md = _make_report().as_markdown()
    assert "call_001.wav" in md


def test_report_markdown_contains_wer_header() -> None:
    md = _make_report().as_markdown()
    assert "WER" in md


def test_report_json_roundtrip() -> None:
    report = _make_report()
    data = report.as_json()
    assert data["backend"] == "faster-whisper"
    assert data["mean_wer"] == pytest.approx(0.0)
    assert len(data["results"]) == 1


def test_report_json_hallucination_flag() -> None:
    result = FileBenchmarkResult(
        filename="x.wav",
        reference="yes",
        hypothesis="yes please go ahead now",
        wer=4.0,
        confidence=0.3,
        latency_ms=200.0,
        hallucination=True,
    )
    report = BenchmarkReport(
        backend="faster-whisper",
        model="tiny.en",
        mean_wer=4.0,
        mean_confidence=0.3,
        mean_latency_ms=200.0,
        results=[result],
    )
    data = report.as_json()
    assert data["results"][0]["hallucination"] is True
