from ivr_assessor.prompt_intelligence import PromptClassification, PromptIntent
from ivr_assessor.scenario_runner import NextActionKind, choose_next_action


def test_choose_next_action_prefers_dtmf_for_confident_menu() -> None:
    classification = PromptClassification(
        intent=PromptIntent.MENU,
        confidence=0.8,
        prompt_signature="please press 2 for billing",
        branch_hint="2",
    )

    action = choose_next_action(
        classification,
        exploration_budget=3,
        confidence_threshold=0.6,
    )

    assert action.kind == NextActionKind.SEND_DTMF
    assert action.payload == "2"


def test_choose_next_action_prefers_dtmf_on_confidence_threshold() -> None:
    classification = PromptClassification(
        intent=PromptIntent.MENU,
        confidence=0.6,
        prompt_signature="press 7 for support",
        branch_hint="7",
    )

    action = choose_next_action(
        classification,
        exploration_budget=1,
        confidence_threshold=0.6,
    )

    assert action.kind == NextActionKind.SEND_DTMF
    assert action.payload == "7"


def test_choose_next_action_extracts_multi_digit_branch() -> None:
    classification = PromptClassification(
        intent=PromptIntent.MENU,
        confidence=0.7,
        prompt_signature="press 10 for operator",
        branch_hint="10",
    )

    action = choose_next_action(
        classification,
        exploration_budget=1,
        confidence_threshold=0.6,
    )

    assert action.kind == NextActionKind.SEND_DTMF
    assert action.payload == "10"


def test_choose_next_action_uses_default_branch_when_hint_missing() -> None:
    classification = PromptClassification(
        intent=PromptIntent.MENU,
        confidence=0.7,
        prompt_signature="press for operator",
        branch_hint=None,
    )

    action = choose_next_action(
        classification,
        exploration_budget=1,
        confidence_threshold=0.6,
    )

    assert action.kind == NextActionKind.SEND_DTMF
    assert action.payload == "1"


def test_choose_next_action_waits_when_uncertain_but_budget_remains() -> None:
    classification = PromptClassification(
        intent=PromptIntent.REQUEST,
        confidence=0.2,
        prompt_signature="say your account number",
        branch_hint=None,
    )

    action = choose_next_action(
        classification,
        exploration_budget=2,
        confidence_threshold=0.6,
    )

    assert action.kind == NextActionKind.WAIT
    assert action.payload is None


def test_choose_next_action_ends_call_when_uncertain_and_budget_exhausted() -> None:
    classification = PromptClassification(
        intent=PromptIntent.REQUEST,
        confidence=0.2,
        prompt_signature="say your account number",
        branch_hint=None,
    )

    action = choose_next_action(
        classification,
        exploration_budget=0,
        confidence_threshold=0.6,
    )

    assert action.kind == NextActionKind.END_CALL
    assert action.payload is None
