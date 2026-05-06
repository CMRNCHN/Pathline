from typing import Any, Sequence

from ivr_assessor.discovery_loop import (
    SessionOutcome,
    plan_dfs_path,
    run_discovery_loop,
)


def test_plan_dfs_path_empty_graph() -> None:
    assert plan_dfs_path({}) == []


def test_plan_dfs_path_shallow_unexplored() -> None:
    graph = {
        "welcome": {
            "announced_options": ["1", "2", "3"],
            "branches": {},
            "observations": 1,
        }
    }
    # Deepest path is length 1. It should pick "1" as it sorts first.
    assert plan_dfs_path(graph) == ["1"]


def test_plan_dfs_path_deep_unexplored() -> None:
    graph = {
        "welcome": {
            "announced_options": ["1"],
            "branches": {
                "1": {"count": 1, "next_prompts": ["sales"]}
            },
            "observations": 1,
        },
        "sales": {
            "announced_options": ["3", "4"],
            "branches": {
                "3": {"count": 1, "next_prompts": ["voicemail"]}
            },
            "observations": 1,
        },
        "voicemail": {
            "announced_options": ["9"],
            "branches": {},
            "observations": 1,
        },
    }
    # Two unexplored nodes exist:
    # - "4" on the sales prompt (path length 2: ["1", "4"])
    # - "9" on the voicemail prompt (path length 3: ["1", "3", "9"])
    # It should pick the deepest path.
    assert plan_dfs_path(graph) == ["1", "3", "9"]


def test_plan_dfs_path_cycle_termination() -> None:
    graph = {
        "welcome": {
            "announced_options": ["1"],
            "branches": {
                "1": {"count": 1, "next_prompts": ["welcome"]}
            },
            "observations": 2,
        }
    }
    # It's a pure cycle that has been fully explored. 
    # It should return an empty list to indicate no un-walked nodes remain.
    assert plan_dfs_path(graph) == []


def test_plan_dfs_path_cycle_with_escape() -> None:
    graph = {
        "root": {
            "announced_options": ["1"],
            "branches": {
                "1": {"count": 1, "next_prompts": ["menu"]}
            },
            "observations": 1,
        },
        "menu": {
            "announced_options": ["1", "2"],
            "branches": {
                "1": {"count": 1, "next_prompts": ["root"]}
            },
            "observations": 1,
        },
    }
    # DFS should traverse root -> 1 -> menu, then see "2" is unexplored.
    # The "1" on the menu loops back to root, which is prevented by the seen set.
    assert plan_dfs_path(graph) == ["1", "2"]


class FakeMapper:
    """Mock mapper to inject predictable graphs without CallEvent overhead."""
    def __init__(self, initial_graph: dict[str, Any] | None = None) -> None:
        self._graph = initial_graph or {}

    def graph(self) -> dict[str, Any]:
        return self._graph


def test_run_discovery_loop_stops_on_max_calls() -> None:
    mapper = FakeMapper()

    def runner(target: str, path: Sequence[str], m: Any) -> SessionOutcome:
        # Always add a new node so we never trigger the no-progress limit
        m._graph[f"node_{len(m._graph)}"] = {"announced_options": ["1"]}
        return SessionOutcome(nodes_added=1, branches_walked=0, events=1)

    _, report = run_discovery_loop(
        target_number="+15550100",
        runner=runner,
        max_calls=3,
        no_progress_limit=10,
        initial_mapper=mapper,  # type: ignore[arg-type]
    )

    assert report.calls == 3
    assert report.stopped_reason == "hit max_calls cap of 3"
    assert len(report.paths_walked) == 3


def test_run_discovery_loop_stops_when_all_walked() -> None:
    mapper = FakeMapper()

    def runner(target: str, path: Sequence[str], m: Any) -> SessionOutcome:
        # Return a graph where every announced option has a count > 0
        m._graph["menu"] = {
            "announced_options": ["1"],
            "branches": {"1": {"count": 1}},
        }
        return SessionOutcome(nodes_added=1, branches_walked=1, events=2)

    _, report = run_discovery_loop(
        target_number="+15550100",
        runner=runner,
        initial_mapper=mapper,  # type: ignore[arg-type]
    )

    # It should do exactly 1 call and realize there's nothing left to explore
    assert report.calls == 1
    assert report.stopped_reason == "all announced options walked"


def test_run_discovery_loop_stops_on_no_progress() -> None:
    mapper = FakeMapper()

    def runner(target: str, path: Sequence[str], m: Any) -> SessionOutcome:
        # Do not mutate the graph, simulating a call that discovers nothing
        return SessionOutcome(nodes_added=0, branches_walked=0, events=1)

    _, report = run_discovery_loop(
        target_number="+15550100",
        runner=runner,
        max_calls=10,
        no_progress_limit=2,
        initial_mapper=mapper,  # type: ignore[arg-type]
    )

    assert report.calls == 2
    assert report.stopped_reason == "2 calls in a row added no nodes"


def test_run_discovery_loop_stops_on_runner_error() -> None:
    mapper = FakeMapper()

    def runner(target: str, path: Sequence[str], m: Any) -> SessionOutcome:
        return SessionOutcome(
            nodes_added=0, branches_walked=0, events=0, error="dial failed"
        )

    _, report = run_discovery_loop(
        target_number="+15550100",
        runner=runner,
        initial_mapper=mapper,  # type: ignore[arg-type]
    )

    assert report.calls == 1
    assert report.stopped_reason == "runner error: dial failed"