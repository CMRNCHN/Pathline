from ivr_assessor.prompt_intelligence import (
    ConversationKind,
    PromptIntent,
    classify_prompt,
    extract_branch_hint,
)


def test_classify_menu_prompt_with_previous_kind() -> None:
    classification = classify_prompt(
        "Press 1 for billing, 2 for support",
        previous_kind=ConversationKind.WELCOME,
    )

    assert classification.intent == PromptIntent.MENU
    assert classification.confidence >= 0.5
    assert classification.prompt_signature == "press 1 for billing, 2 for support"
    assert classification.branch_hint == "1"


def test_extract_branch_hint_handles_multi_digit_values() -> None:
    assert extract_branch_hint("press 10 for operator") == "10"


def test_classify_menu_prompt_extracts_multi_digit_branch() -> None:
    classification = classify_prompt("Press 10 for operator")

    assert classification.intent == PromptIntent.MENU
    assert classification.branch_hint == "10"
    assert classification.prompt_signature == "press 10 for operator"


def test_classify_general_prompt_uses_lower_confidence() -> None:
    classification = classify_prompt("Please say your account number.")

    assert classification.intent == PromptIntent.REQUEST
    assert classification.confidence < 0.5
    assert classification.prompt_signature == "please say your account number."
    assert classification.branch_hint is None


def test_classify_prompt_with_for_but_no_menu_language_stays_request() -> None:
    classification = classify_prompt("We are looking for your account number.")

    assert classification.intent == PromptIntent.REQUEST
    assert classification.confidence < 0.5
    assert classification.prompt_signature == "we are looking for your account number."
    assert classification.branch_hint is None
