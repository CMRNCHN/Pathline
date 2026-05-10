"""Iterative IVR discovery loop.

The loop runs many short calls back-to-back, accumulating graph knowledge
between them. Each call lasts at most ~30s (soft cap — the current IVR
prompt is allowed to finish so we don't lose its transcription), and the
next call re-uses the accumulated graph to plan a planned DTMF path that
goes deepest-first (DFS) into options the IVR has *announced* but the
agent has not yet *walked*.

The actual telephony / prompt-source plumbing is injected so this module
can be unit-tested with scripted fakes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from .ivr_mapper import IvrMapper, branch_sort_key


# A `SessionRunner` runs ONE call against `target_number`, follows
# `planned_path` for as long as it still applies, then auto-explores until
# either the 30s soft cap fires or the call ends naturally. It returns the
# events observed and feeds them through the supplied mapper. The runner
# is provided by the caller so this module stays free of telephony/Twilio
# coupling.
SessionRunner = Callable[
    [
        str,            # target_number
        Sequence[str],  # planned_path of DTMF digits to send first
        IvrMapper,      # mutated in place with new observations
    ],
    "SessionOutcome",
]


@dataclass(frozen=True)
class SessionOutcome:
    """Per-call result reported back to the loop."""

    nodes_added: int
    branches_walked: int
    events: int
    aborted: bool = False
    error: str | None = None


@dataclass
class DiscoveryReport:
    target_number: str
    calls: int = 0
    nodes: int = 0
    branches_explored: int = 0
    stopped_reason: str = ""
    history: list[SessionOutcome] = field(default_factory=list)
    paths_walked: list[list[str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "target_number": self.target_number,
            "calls": self.calls,
            "nodes": self.nodes,
            "branches_explored": self.branches_explored,
            "stopped_reason": self.stopped_reason,
            "history": [
                {
                    "nodes_added": h.nodes_added,
                    "branches_walked": h.branches_walked,
                    "events": h.events,
                    "aborted": h.aborted,
                    "error": h.error,
                }
                for h in self.history
            ],
            "paths_walked": [list(p) for p in self.paths_walked],
        }


def plan_dfs_path(graph: Mapping[str, Mapping[str, object]]) -> list[str]:
    """Return the deepest planned DTMF sequence that ends at an unexplored option.

    The path is a list of digits to press from the IVR's root menu. The last
    element is the *unexplored* option we want to walk; every digit before
    it is a known-good branch (count > 0 with at least one observed
    next_prompt) that gets us there.

    Returns an empty list when the graph is empty or every announced option
    has been walked.
    """
    if not graph:
        return []

    # Identify roots (nodes nothing else points to). If everything is in a
    # cycle, fall back to the most-observed prompt as the entry point.
    next_keys: set[str] = set()
    for node in graph.values():
        for branch in (node.get("branches") or {}).values():
            for child in branch.get("next_prompts", []) or []:
                next_keys.add(child)
    roots = [p for p in graph.keys() if p not in next_keys]
    if not roots:
        roots = [
            max(
                graph.keys(),
                key=lambda p: int(graph[p].get("observations", 0) or 0),
            )
        ]

    best_path: list[str] = []

    def walk(prompt: str, path: list[str], seen: frozenset[str]) -> None:
        nonlocal best_path
        if prompt in seen:
            return
        node = graph.get(prompt)
        if node is None:
            return
        seen = seen | {prompt}

        branches = node.get("branches") or {}
        announced = set(node.get("announced_options") or [])

        # Unexplored = announced (or recorded) option with count == 0.
        # If a branch is in `branches` but count==0, treat as unexplored.
        explored: set[str] = set()
        for opt, b in branches.items():
            count = int((b or {}).get("count", 0) or 0)
            if count > 0:
                explored.add(opt)

        all_known = set(branches.keys()) | announced
        unexplored = sorted(
            all_known - explored,
            key=branch_sort_key,
        )

        # Candidate: each unexplored option ends a path. Prefer the deepest
        # — i.e. one that requires the most known steps to reach. Since we
        # only descend through *explored* branches with known next_prompts,
        # we update best_path whenever we find a deeper one.
        for opt in unexplored:
            candidate = path + [opt]
            if len(candidate) > len(best_path):
                best_path = candidate

        # Recurse through explored branches (DFS).
        for opt in sorted(explored, key=branch_sort_key):
            branch = branches.get(opt) or {}
            next_prompts = list(branch.get("next_prompts") or [])
            # Pick a stable next prompt to descend into (sorted) to keep
            # the planning deterministic.
            for nxt in sorted(next_prompts):
                walk(nxt, path + [opt], seen)

    for root in roots:
        walk(root, [], frozenset())

    return best_path


def run_discovery_loop(
    target_number: str,
    runner: SessionRunner,
    *,
    max_calls: int = 12,
    no_progress_limit: int = 2,
    initial_mapper: IvrMapper | None = None,
) -> tuple[IvrMapper, DiscoveryReport]:
    """Run iterative calls until the graph saturates.

    Stopping rules (whichever fires first):
      * `no_progress_limit` consecutive calls add zero new nodes.
      * Every announced option has been walked at least once.
      * `max_calls` reached (safety cap).
    """
    mapper = initial_mapper or IvrMapper()
    report = DiscoveryReport(target_number=target_number)

    consecutive_no_progress = 0

    while report.calls < max_calls:
        graph_before = mapper.graph()
        node_count_before = len(graph_before)
        if node_count_before and _every_option_walked(graph_before):
            report.stopped_reason = "all announced options walked"
            break

        planned = plan_dfs_path(graph_before)
        report.paths_walked.append(list(planned))

        outcome = runner(target_number, planned, mapper)
        report.calls += 1
        report.history.append(outcome)
        if outcome.error:
            report.stopped_reason = f"runner error: {outcome.error}"
            break

        graph_after = mapper.graph()
        nodes_added = len(graph_after) - node_count_before

        if nodes_added <= 0:
            consecutive_no_progress += 1
            if consecutive_no_progress >= no_progress_limit:
                report.stopped_reason = (
                    f"{consecutive_no_progress} calls in a row added no nodes"
                )
                break
        else:
            consecutive_no_progress = 0

    if not report.stopped_reason:
        report.stopped_reason = f"hit max_calls cap of {max_calls}"

    final = mapper.graph()
    report.nodes = len(final)
    report.branches_explored = sum(
        1
        for node in final.values()
        for b in (node.get("branches") or {}).values()
        if int((b or {}).get("count", 0) or 0) > 0
    )

    return mapper, report


def _every_option_walked(graph: Mapping[str, Mapping[str, object]]) -> bool:
    """True when every announced option on every node has count >= 1."""
    for node in graph.values():
        announced = set(node.get("announced_options") or [])
        if not announced:
            continue
        branches = node.get("branches") or {}
        for opt in announced:
            branch = branches.get(opt) or {}
            if int((branch or {}).get("count", 0) or 0) <= 0:
                return False
    return True


__all__ = [
    "DiscoveryReport",
    "SessionOutcome",
    "SessionRunner",
    "plan_dfs_path",
    "run_discovery_loop",
]
