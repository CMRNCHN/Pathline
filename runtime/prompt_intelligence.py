from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class PromptIntent(StrEnum):
    MENU = "menu"
    REQUEST = "request"
    UNKNOWN = "unknown"


class ConversationKind(StrEnum):
    WELCOME = "welcome"
    MENU = "menu"
    REQUEST = "request"


@dataclass(frozen=True)
class PromptClassification:
    intent: PromptIntent
    confidence: float
    prompt_signature: str
    branch_hint: str | None = None
    options: list[str] = field(default_factory=list)


def _extract_first_branch(text: str) -> str | None:
    """Returns the first DTMF digit(s) following a menu keyword, supporting multi-digit values."""
    match = re.search(r"(?:press|dial|enter|for)\s+(\d+)", text.lower())
    return match.group(1) if match else None


def _extract_all_branches(text: str) -> list[str]:
    """Returns all DTMF options present in the text, deduped and sorted."""
    return sorted(set(re.findall(r"(?:press|dial|enter|for)\s+(\d+)", text.lower())))


def classify_prompt(
    prompt: str,
    previous_kind: ConversationKind | None = None,  # noqa: ARG001 — reserved for future context-aware logic
) -> PromptClassification:
    lowered = prompt.lower()
    prompt_signature = lowered[:64]

    options = _extract_all_branches(prompt)
    branch_hint = options[0] if options else None

    if branch_hint:
        return PromptClassification(
            intent=PromptIntent.MENU,
            confidence=0.85,
            prompt_signature=prompt_signature,
            branch_hint=branch_hint,
            options=options,
        )

    if "for billing" in lowered or "for support" in lowered:
        return PromptClassification(
            intent=PromptIntent.MENU,
            confidence=0.7,
            prompt_signature=prompt_signature,
            branch_hint=None,
        )

    return PromptClassification(
        intent=PromptIntent.REQUEST,
        confidence=0.4,
        prompt_signature=prompt_signature,
        branch_hint=None,
    )


def extract_branch_hint(action_text: str) -> str | None:
    """Extracts a branch identifier from an action string or a free-text prompt.

    Handles both the internal "dtmf:<digits>" format used by action events and
    free-text phrases like "press 10 for operator".
    """
    if action_text.startswith("dtmf:"):
        return action_text.split(":", 1)[1]
    return _extract_first_branch(action_text)