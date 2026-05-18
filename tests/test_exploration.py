from runtime.exploration import CandidateAction, choose_candidate


def test_choose_candidate_proposes_least_explored_branch() -> None:
    graph = {
        "Press 1 for billing": {
            "observations": 2,
            "sessions": ["s1", "s2"],
            "branches": {
                "1": {"count": 2, "sessions": ["s1", "s2"], "next_prompts": []},
                "2": {"count": 1, "sessions": ["s3"], "next_prompts": []},
            },
        }
    }

    action = choose_candidate(
        graph=graph,
        observed_prompt="Press 1 for billing",
        exploration_budget=3,
    )

    assert action == CandidateAction(kind="send_dtmf", payload="2")


def test_choose_candidate_waits_for_unknown_prompt() -> None:
    action = choose_candidate(
        graph={},
        observed_prompt="Press 1 for billing",
        exploration_budget=3,
    )

    assert action == CandidateAction(kind="wait")


def test_choose_candidate_ends_call_when_budget_exhausted() -> None:
    action = choose_candidate(
        graph={},
        observed_prompt="Press 1 for billing",
        exploration_budget=0,
    )

    assert action == CandidateAction(kind="end_call")