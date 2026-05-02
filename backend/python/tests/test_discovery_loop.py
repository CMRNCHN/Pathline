from __future__ import annotations

from ivr_assessor.discovery_loop import (
    SessionOutcome,
    plan_dfs_path,
    run_discovery_loop,
)
from ivr_assessor.ivr_mapper import IvrMapper
from ivr_assessor.models import CallEvent


# ─────────────────────────────────────────────────────────────────────────────
# plan_dfs_path
# ─────────────────────────────────────────────────────────────────────────────

def test_plan_dfs_path_empty_graph_returns_empty_list() -> None:
    assert plan_dfs_path({}) == []


def test_plan_dfs_path_picks_unexplored_option_at_root() -> None:
    mapper = IvrMapper()
    mapper.observe(
        CallEvent(kind="prompt", text="Press 1 for billing or 2 for support", t_ms=0),
        branch_confidence=0.9,
        session_id="s1",
    )
    # No DTMF sent — both 1 and 2 are announced but unexplored.
    path = plan_dfs_path(mapper.graph())
    assert path in (["1"], ["2"])  # either is a valid first step


def test_plan_dfs_path_descends_into_walked_branches() -> None:
    """When the root has been explored down branch 1 to a child menu with
    further announced options, the path should be ["1", <child_option>]."""
    mapper = IvrMapper()
    mapper.observe(
        CallEvent(kind="prompt", text="Press 1 for billing or 2 for support", t_ms=0),
        branch_confidence=0.9,
        session_id="s1",
    )
    mapper.observe(
        CallEvent(kind="action", text="dtmf:1", t_ms=100),
        branch_confidence=0.9,
        session_id="s1",
    )
    mapper.observe(
        CallEvent(kind="prompt", text="Press 3 for invoices or 4 for payments", t_ms=200),
        branch_confidence=0.9,
        session_id="s1",
    )
    path = plan_dfs_path(mapper.graph())
    assert len(path) == 2
    assert path[0] == "1"
    assert path[1] in ("3", "4")


def test_plan_dfs_path_returns_empty_when_everything_walked() -> None:
    mapper = IvrMapper()
    mapper.observe(
        CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0),
        branch_confidence=0.9,
        session_id="s1",
    )
    mapper.observe(
        CallEvent(kind="action", text="dtmf:1", t_ms=100),
        branch_confidence=0.9,
        session_id="s1",
    )
    mapper.observe(
        CallEvent(kind="prompt", text="Billing menu", t_ms=200),
        branch_confidence=0.9,
        session_id="s1",
    )
    # Root only announces "1", and we've walked it. The Billing menu has no
    # branches at all (request, not menu) — so nothing to explore.
    assert plan_dfs_path(mapper.graph()) == []


# ─────────────────────────────────────────────────────────────────────────────
# run_discovery_loop
# ─────────────────────────────────────────────────────────────────────────────

def test_run_discovery_loop_stops_after_two_no_progress_calls() -> None:
    """A runner that never adds nodes should trigger the no-progress stop."""
    calls: list[list[str]] = []

    def runner(target, planned, mapper):
        calls.append(list(planned))
        return SessionOutcome(nodes_added=0, branches_walked=0, events=0)

    _, report = run_discovery_loop(
        target_number="+15555550100",
        runner=runner,
        max_calls=10,
        no_progress_limit=2,
    )

    assert len(calls) == 2
    assert report.calls == 2
    assert "added no nodes" in report.stopped_reason


def test_run_discovery_loop_stops_when_every_option_walked() -> None:
    """Once all announced options have been walked, the loop stops cleanly."""

    def runner(target, planned, mapper):
        # First call seeds a single-option menu and walks it.
        if not mapper.graph():
            mapper.observe(
                CallEvent(kind="prompt", text="Press 1 for billing", t_ms=0),
                branch_confidence=0.9,
                session_id="s1",
            )
            mapper.observe(
                CallEvent(kind="action", text="dtmf:1", t_ms=100),
                branch_confidence=0.9,
                session_id="s1",
            )
            mapper.observe(
                CallEvent(kind="prompt", text="Billing menu", t_ms=200),
                branch_confidence=0.9,
                session_id="s1",
            )
            return SessionOutcome(nodes_added=2, branches_walked=1, events=3)
        # Subsequent calls — should not be invoked since everything is walked.
        return SessionOutcome(nodes_added=0, branches_walked=0, events=0)

    mapper, report = run_discovery_loop(
        target_number="+15555550100",
        runner=runner,
        max_calls=10,
    )

    assert report.calls == 1
    assert "all announced options walked" in report.stopped_reason
    assert report.nodes == 2


def test_run_discovery_loop_respects_max_calls() -> None:
    """Even with progress every call, the safety cap fires."""
    counter = {"i": 0}

    def runner(target, planned, mapper):
        counter["i"] += 1
        # Always seed a *new* unique prompt so no-progress never triggers.
        mapper.observe(
            CallEvent(
                kind="prompt",
                text=f"Press 1 for option {counter['i']}",
                t_ms=0,
            ),
            branch_confidence=0.9,
            session_id=f"s{counter['i']}",
        )
        return SessionOutcome(nodes_added=1, branches_walked=0, events=1)

    _, report = run_discovery_loop(
        target_number="+15555550100",
        runner=runner,
        max_calls=3,
    )
    assert report.calls == 3
    assert "max_calls" in report.stopped_reason
