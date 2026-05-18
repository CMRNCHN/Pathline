"""Tests for transcript_filter.py — dedup + length gate."""
from __future__ import annotations

from runtime.media.transcript_filter import TranscriptFilter


def _make_filter(window_size: int = 3) -> tuple[TranscriptFilter, list[str]]:
    received: list[str] = []
    f = TranscriptFilter(
        on_transcript=lambda text, final, sfinal: received.append(text),
        window_size=window_size,
    )
    return f, received


def _call(f: TranscriptFilter, text: str) -> None:
    f(text, is_final=True, speech_final=True)


# ─── Length gate ──────────────────────────────────────────────────────────────

def test_passes_normal_text() -> None:
    f, received = _make_filter()
    _call(f, "press one for billing")
    assert received == ["press one for billing"]


def test_drops_empty_string() -> None:
    f, received = _make_filter()
    _call(f, "")
    assert received == []


def test_drops_single_char() -> None:
    f, received = _make_filter()
    _call(f, "a")
    assert received == []


def test_passes_two_char_string() -> None:
    f, received = _make_filter()
    _call(f, "ok")
    assert received == ["ok"]


def test_drops_whitespace_only() -> None:
    f, received = _make_filter()
    _call(f, "   ")
    assert received == []


# ─── Deduplication ────────────────────────────────────────────────────────────

def test_drops_exact_duplicate_in_window() -> None:
    f, received = _make_filter()
    _call(f, "press one")
    _call(f, "press one")  # duplicate — dropped
    assert received == ["press one"]


def test_allows_after_window_rolls_past() -> None:
    f, received = _make_filter(window_size=2)
    _call(f, "press one")   # window: ["press one"]
    _call(f, "press two")   # window: ["press one", "press two"]
    _call(f, "press three") # window: ["press two", "press three"] — "press one" evicted
    _call(f, "press one")   # should pass again
    assert "press one" in received
    assert received.count("press one") == 2


def test_dedup_is_case_insensitive() -> None:
    f, received = _make_filter()
    _call(f, "Yes")
    _call(f, "yes")   # same after normalize
    assert received == ["Yes"]


def test_dedup_strips_punctuation() -> None:
    f, received = _make_filter()
    _call(f, "Press one.")
    _call(f, "Press one")   # same normalized form: "press one"
    assert len(received) == 1


def test_different_texts_both_pass() -> None:
    f, received = _make_filter()
    _call(f, "press one")
    _call(f, "press two")
    assert received == ["press one", "press two"]


# ─── Flags forwarded ──────────────────────────────────────────────────────────

def test_speech_final_flag_preserved() -> None:
    finals: list[bool] = []
    f = TranscriptFilter(on_transcript=lambda t, fin, sf: finals.append(sf))
    f("press one", is_final=True, speech_final=True)
    f("press two", is_final=True, speech_final=False)
    assert finals == [True, False]


def test_is_final_flag_preserved() -> None:
    is_finals: list[bool] = []
    f = TranscriptFilter(on_transcript=lambda t, fin, sf: is_finals.append(fin))
    f("press one", is_final=False, speech_final=True)
    assert is_finals == [False]


# ─── reset() ──────────────────────────────────────────────────────────────────

def test_reset_clears_dedup_window() -> None:
    f, received = _make_filter()
    _call(f, "press one")
    f.reset()
    _call(f, "press one")  # window cleared — should pass again
    assert received.count("press one") == 2


# ─── stats() ─────────────────────────────────────────────────────────────────

def test_stats_counts_accurately() -> None:
    f, _ = _make_filter()
    _call(f, "press one")   # passed
    _call(f, "press one")   # dedup dropped
    _call(f, "a")           # short dropped
    _call(f, "press two")   # passed
    s = f.stats()
    assert s["received"] == 4
    assert s["passed"] == 2
    assert s["dropped_dedup"] == 1
    assert s["dropped_short"] == 1


def test_stats_initial_all_zeros() -> None:
    f, _ = _make_filter()
    s = f.stats()
    assert all(v == 0 for v in s.values())