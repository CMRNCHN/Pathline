from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from agents.prompt_intelligence import PromptClassification, PromptIntent


class NextActionKind(StrEnum):
    SEND_DTMF = "send_dtmf"
    PLAY_CLIP = "play_clip"
    WAIT = "wait"
    END_CALL = "end_call"


@dataclass(frozen=True)
class NextAction:
    kind: NextActionKind
    payload: str | None = None


def choose_next_action(
    classification: PromptClassification,
    exploration_budget: int,
    confidence_threshold: float,
) -> NextAction:
    is_confident_menu = (
        classification.intent == PromptIntent.MENU
        and classification.confidence >= confidence_threshold
    )
    if is_confident_menu:
        return NextAction(
            kind=NextActionKind.SEND_DTMF,
            payload=classification.branch_hint or "1",
        )

    if exploration_budget > 0:
        return NextAction(kind=NextActionKind.WAIT)

    return NextAction(kind=NextActionKind.END_CALL)