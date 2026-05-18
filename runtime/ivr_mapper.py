from __future__ import annotations

import re
from dataclasses import dataclass, field

from runtime.state.models import CallEvent
from runtime.prompt_intelligence import classify_prompt, extract_branch_hint


_PUNCT_TAIL = re.compile(r"[\s\.\,\!\?\;\:\-—–]+$")
_WHITESPACE = re.compile(r"\s+")


def _normalize_prompt(text: str) -> str:
    """Canonical key for grouping near-duplicate prompts.

    Collapses runs of whitespace, strips trailing punctuation, and lowercases.
    Used only as a *grouping key* — the original prompt text is preserved as
    the displayed label so the GUI still shows what the IVR actually said.
    """
    if not text:
        return ""
    collapsed = _WHITESPACE.sub(" ", text).strip()
    collapsed = _PUNCT_TAIL.sub("", collapsed)
    return collapsed.lower()


@dataclass
class BranchObservation:
    branch: str
    count: int = 0
    sessions: set[str] = field(default_factory=set)
    next_prompts: set[str] = field(default_factory=set)
    confidence: float = 0.0
    # Running confidence across observations of this branch.
    _confidence_total: float = 0.0
    _confidence_n: int = 0


@dataclass
class PromptNode:
    prompt: str
    observations: int = 0
    sessions: set[str] = field(default_factory=set)
    branches: dict[str, BranchObservation] = field(default_factory=dict)
    confidence: float = 0.0
    # Options the IVR actually announced (e.g. "press 1 for billing, 2 for
    # support" → {"1", "2"}). These are *known* even if the agent hasn't
    # walked them yet, and are surfaced separately so the GUI can show
    # remaining-to-explore branches without polluting the explored-branch
    # counts.
    announced_options: set[str] = field(default_factory=set)
    # Running confidence across observations of the prompt itself.
    _confidence_total: float = 0.0
    _confidence_n: int = 0


@dataclass
class _SessionState:
    current_key: str | None = None
    pending_branch: str | None = None


class IvrMapper:
    """Builds an IVR graph from prompt + action call events.

    Two key improvements over a raw text-keyed graph:
      1. Prompts are grouped by a normalized key so cosmetically different
         observations (trailing punctuation, casing, whitespace) merge into
         one node.
      2. When a prompt is classified as a menu, every announced option is
         recorded on the node's ``announced_options`` set so the renderer
         can show the full menu — including options the agent has not yet
         walked — without changing the per-branch ``count`` semantics.
    """

    def __init__(self) -> None:
        # node_key -> PromptNode. Keys are normalized; node.prompt is the
        # canonical display text (the longest representative we've seen).
        self._nodes: dict[str, PromptNode] = {}
        self._sessions: dict[str, _SessionState] = {}

    def observe(self, event: CallEvent, branch_confidence: float, session_id: str) -> None:
        session = self._sessions.setdefault(session_id, _SessionState())
        if event.kind == "prompt":
            self._observe_prompt(event.text, branch_confidence, session_id, session)
            return
        if event.kind == "action":
            self._observe_action(event.text, branch_confidence, session_id, session)

    def graph(self) -> dict[str, dict[str, object]]:
        """Return the graph keyed by canonical prompt text for stable rendering."""
        return {
            node.prompt: {
                "observations": node.observations,
                "confidence": round(node.confidence, 4),
                "sessions": sorted(node.sessions),
                "announced_options": sorted(node.announced_options, key=branch_sort_key),
                "branches": {
                    branch: {
                        "count": observation.count,
                        "confidence": round(observation.confidence, 4),
                        "sessions": sorted(observation.sessions),
                        "next_prompts": sorted(observation.next_prompts),
                    }
                    for branch, observation in sorted(
                        node.branches.items(), key=_branch_sort_key
                    )
                },
            }
            for node in sorted(self._nodes.values(), key=lambda n: n.prompt)
        }

    # ────────────────────────────────────────────────────────────────────────
    # internals
    # ────────────────────────────────────────────────────────────────────────

    def _observe_prompt(
        self,
        prompt: str,
        branch_confidence: float,
        session_id: str,
        session: _SessionState,
    ) -> None:
        key = _normalize_prompt(prompt)
        if not key:
            return

        # Wire the prior session step's pending branch to this prompt as the
        # observed downstream prompt. We use the canonical text so the
        # rendered graph deduplicates correctly.
        if session.current_key is not None and session.pending_branch is not None:
            previous_node = self._nodes.get(session.current_key)
            if previous_node is not None:
                obs = previous_node.branches.setdefault(
                    session.pending_branch,
                    BranchObservation(branch=session.pending_branch),
                )
                node_for_next = self._ensure_node(key, prompt)
                obs.next_prompts.add(node_for_next.prompt)

        node = self._ensure_node(key, prompt)
        node.observations += 1
        node.sessions.add(session_id)
        _accumulate_confidence(node, branch_confidence)

        # Record announced options so the GUI can show the full menu — but
        # *do not* seed entries in `branches`, since that dict tracks
        # actual presses (count, sessions). Renderers union the two sets.
        classification = classify_prompt(prompt)
        for option in classification.options:
            node.announced_options.add(option)

        session.current_key = key
        session.pending_branch = None

    def _observe_action(
        self,
        action_text: str,
        branch_confidence: float,
        session_id: str,
        session: _SessionState,
    ) -> None:
        if session.current_key is None:
            return

        branch = extract_branch_hint(action_text)
        if branch is None:
            return

        node = self._nodes.get(session.current_key)
        if node is None:
            return

        observation = node.branches.setdefault(branch, BranchObservation(branch=branch))
        observation.count += 1
        observation.sessions.add(session_id)
        _accumulate_confidence(observation, branch_confidence)

        session.pending_branch = branch

    def _ensure_node(self, key: str, prompt: str) -> PromptNode:
        node = self._nodes.get(key)
        if node is None:
            node = PromptNode(prompt=prompt)
            self._nodes[key] = node
            return node
        # Prefer the longest-seen variant as the canonical display label so
        # the graph shows the most informative version of the prompt.
        if len(prompt) > len(node.prompt):
            node.prompt = prompt
        return node


def _accumulate_confidence(target: PromptNode | BranchObservation, value: float) -> None:
    """Maintain a running average so flukes don't dominate the score."""
    target._confidence_total += value  # type: ignore[attr-defined]
    target._confidence_n += 1  # type: ignore[attr-defined]
    target.confidence = target._confidence_total / max(1, target._confidence_n)  # type: ignore[attr-defined]


def branch_sort_key(branch: str) -> tuple[int, str]:
    """Sort key that orders numeric branches naturally (1, 2, 10) instead of (1, 10, 2)."""
    try:
        return (0, f"{int(branch):020d}")
    except ValueError:
        return (1, branch)


def _branch_sort_key(item: tuple[str, BranchObservation]) -> tuple[int, str]:
    return branch_sort_key(item[0])