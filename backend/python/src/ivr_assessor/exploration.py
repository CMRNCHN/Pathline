from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CandidateAction:
    kind: str
    payload: str | None = None


def choose_candidate(
    graph: Mapping[str, Mapping[str, object]],
    observed_prompt: str,
    exploration_budget: int,
    available_options: list[str] | None = None,
) -> CandidateAction:
    """Chooses the least-explored branch for the observed prompt.

    If available_options is None, options are derived from the graph's recorded
    branches for that prompt.
    """
    if exploration_budget <= 0:
        return CandidateAction(kind="end_call")

    node = graph.get(observed_prompt)

    if available_options is None:
        if node is None or not isinstance(node.get("branches"), Mapping):
            return CandidateAction(kind="wait")
        available_options = list(node["branches"].keys())

    if not available_options:
        return CandidateAction(kind="wait")

    if node is None or not isinstance(node.get("branches"), Mapping):
        return CandidateAction(kind="send_dtmf", payload=available_options[0])

    branches = node["branches"]
    branch_counts: dict[str, int] = {}
    for option in available_options:
        branch_state = branches.get(option)
        count = 0
        if isinstance(branch_state, Mapping):
            raw_count = branch_state.get("count", 0)
            if isinstance(raw_count, int):
                count = raw_count
        branch_counts[option] = count

    sorted_options = sorted(branch_counts.items(), key=lambda item: (item[1], item[0]))
    return CandidateAction(kind="send_dtmf", payload=sorted_options[0][0])
