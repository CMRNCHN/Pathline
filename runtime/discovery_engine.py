"""IVR Agent Discovery Engine — Phase 1 (passive, read-only).

The DiscoveryEngine runs after every call (manual or autonomous).  It reads
the world model held in an IvrMapper, computes what the agent does NOT yet
know, and emits GapTask records into a GapTaskQueue.

In Phase 1 the engine is entirely PASSIVE:
  - It reads the mapper graph and session observations.
  - It generates and queues GapTasks.
  - It dispatches nothing autonomously.
  - Every generated task has status=PENDING and source_engine='discovery'.

Typical call site (end of a session):

    from runtime.discovery_engine import DiscoveryEngine
    from runtime.gap_task import GapTaskQueue

    queue = GapTaskQueue()
    engine = DiscoveryEngine(queue)
    tasks = engine.classify_gaps(
        session_id="session-abc",
        system_id="1-800-555-0100",
        mapper=mapper,
        session_observations=observations,
    )
    logger.info("generated %d gap tasks", len(tasks))

StorageBackend is accepted as an optional parameter so callers that already
have a persistence layer can pass it in.  The engine itself uses the mapper
in-memory; persistence is the caller's responsibility.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Sequence

from runtime.ivr_mapper import IvrMapper
from runtime.storage import StorageBackend, SessionObservation as StorageSessionObservation
from runtime.node_view import NodeView as PromptNode, build_node_views
from runtime.gap_task import (
    GapTask,
    GapTaskQueue,
    GapType,
    GapStatus,
    PriorityScoreBreakdown,
)
from runtime.prompt_intelligence import classify_prompt, PromptIntent

logger = logging.getLogger(__name__)


# SessionObservation and StorageBackend are imported from runtime.storage.
# The local stubs below were removed — use the real implementations.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRANSFER_KEYWORDS = re.compile(
    r"\b(transfer|agent|representative|operator|hold|connect|specialist)\b",
    re.IGNORECASE,
)

_AUTH_KEYWORDS = re.compile(
    r"\b(account number|pin|password|social security|ssn|date of birth|dob"
    r"|zip code|authenticate|verify your identity)\b",
    re.IGNORECASE,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _hours_since(dt: datetime) -> float:
    return (_now_utc() - dt).total_seconds() / 3600.0


def _is_menu_node(node: PromptNode) -> bool:
    """True when the node announces DTMF options or classifies as MENU intent."""
    if node.announced_options:
        return True
    classification = classify_prompt(node.prompt)
    return classification.intent == PromptIntent.MENU


def _leads_to_transfer(node_key: str, nodes: dict[str, PromptNode]) -> bool:
    """Heuristic BFS: does the subgraph reachable from node_key contain a transfer node?"""
    visited: set[str] = set()
    queue: list[str] = [node_key]
    while queue:
        current_key = queue.pop()
        if current_key in visited:
            continue
        visited.add(current_key)
        node = nodes.get(current_key)
        if node is None:
            continue
        if _TRANSFER_KEYWORDS.search(node.prompt):
            return True
        for branch in node.branches.values():
            for next_prompt in branch.next_prompts:
                # next_prompts store canonical display text; find the node key
                for k, n in nodes.items():
                    if n.prompt == next_prompt and k not in visited:
                        queue.append(k)
    return False


def _is_auth_gate(node: PromptNode) -> bool:
    return bool(_AUTH_KEYWORDS.search(node.prompt))


# ---------------------------------------------------------------------------
# DiscoveryEngine
# ---------------------------------------------------------------------------

class DiscoveryEngine:
    """Analyses the IVR world model and emits GapTasks for everything unknown.

    Parameters
    ----------
    queue:
        The shared GapTaskQueue this engine writes into.
    storage:
        Optional persistence backend.  If omitted, an in-memory no-op is used.
    default_user_priority:
        Operator-assigned weight applied to all generated tasks.  Default 0.5.
    """

    def __init__(
        self,
        queue: GapTaskQueue,
        storage: StorageBackend | None = None,
        default_user_priority: float = 0.5,
    ) -> None:
        self._queue = queue
        self._storage = storage or StorageBackend()
        self._default_user_priority = default_user_priority

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def classify_gaps(
        self,
        session_id: str,
        system_id: str,
        mapper: IvrMapper,
        session_observations: Sequence[StorageSessionObservation] | None = None,
    ) -> list[GapTask]:
        """Analyse the world model and emit GapTasks for all detected gaps.

        Called at the end of every session.  This method is idempotent with
        respect to duplicates: existing PENDING/IN_PROGRESS tasks for the
        same (gap_type, target_node, trigger_value) are refreshed rather
        than duplicated.

        Parameters
        ----------
        session_id:
            The session that just ended; recorded as the source of new tasks.
        system_id:
            IVR identifier (phone number or logical ID).
        mapper:
            The populated IvrMapper for this system.
        session_observations:
            Raw STT observations from the session, used by detectors that
            need per-session signal (ambiguous prompts).

        Returns
        -------
        list[GapTask]
            All tasks generated (new + refreshed) during this call.
        """
        # Load session observations from storage if not provided directly
        if session_observations is not None:
            observations: list[StorageSessionObservation] = list(session_observations)
        elif session_id and hasattr(self._storage, 'get_observations_for_session'):
            observations = self._storage.get_observations_for_session(session_id)
        else:
            observations = []
        nodes: dict[str, PromptNode] = build_node_views(system_id, self._storage)

        # Load existing PENDING / IN_PROGRESS gaps for deduplication.
        existing = self._storage.load_existing_gaps(
            system_id,
            statuses=[GapStatus.PENDING, GapStatus.IN_PROGRESS],
        )
        existing_index: dict[tuple[str, str | None, str | None], GapTask] = {
            (str(g.gap_type), getattr(g, 'target_node_key', None) or getattr(g, 'target_node_id', None), g.target_option): g
            for g in existing
        }

        # Also index tasks already in the in-memory queue so we de-dup even
        # when no storage backend is wired.
        for gap in list(self._queue._all.values()):  # noqa: SLF001
            if gap.status in (GapStatus.PENDING, GapStatus.IN_PROGRESS):
                key = (str(gap.gap_type), gap.target_node_key, gap.target_option)
                existing_index.setdefault(key, gap)

        # Collect DTMFs pressed this session that may not yet have linked edges
        session_dtmf_pressed: set[str] = set()
        for obs in observations:
            kind = str(getattr(obs, 'event_kind', '') or getattr(obs, 'event_type', '')).lower()
            if 'dtmf' in kind:
                payload = getattr(obs, 'raw_payload', None) or {}
                dtmf_val = (payload.get('dtmf_value') or payload.get('dtmf') or
                            getattr(obs, 'dtmf_value', '') or getattr(obs, 'event_text', '') or '')
                if dtmf_val:
                    session_dtmf_pressed.add(str(dtmf_val))

        # ---- Collect candidates from all detectors ----
        candidates: list[GapTask] = []
        candidates.extend(
            self._detect_unvisited_announced_options(nodes, session_id, system_id, session_dtmf_pressed)
        )
        candidates.extend(self._detect_unconfirmed_edges(nodes, session_id, system_id))
        candidates.extend(
            self._detect_variable_behavior(nodes, observations, session_id, system_id)
        )
        candidates.extend(
            self._detect_ambiguous_prompts(observations, session_id, system_id)
        )
        candidates.extend(
            self._detect_timeout_unknowns(nodes, session_id, system_id)
        )
        candidates.extend(
            self._detect_post_auth_unknowns(nodes, session_id, system_id)
        )
        candidates.extend(
            self._generate_announcement_hypotheses(nodes, session_id, system_id)
        )

        # ---- Deduplication and queue insertion ----
        generated: list[GapTask] = []
        for gap in candidates:
            dedup_key = (str(gap.gap_type), gap.target_node_key, gap.target_option)
            existing_gap = existing_index.get(dedup_key)

            if existing_gap is not None:
                # Refresh priority and freshness; do not create a duplicate.
                existing_gap.priority_score = gap.priority_score
                existing_gap.score_breakdown = gap.score_breakdown
                existing_gap.updated_at = _now_utc()
                self._storage.update_gap(existing_gap)
                generated.append(existing_gap)
                logger.debug(
                    "refreshed existing gap %s (%s)",
                    existing_gap.gap_id,
                    existing_gap.gap_type,
                )
            else:
                # Brand new gap.
                existing_index[dedup_key] = gap
                try:
                    self._queue.push(gap)
                except ValueError:
                    # Race: already in queue from a concurrent call.  Skip.
                    pass
                else:
                    self._storage.save_gap(gap)
                    generated.append(gap)
                    logger.debug(
                        "created gap %s (%s) node=%s option=%s score=%.3f",
                        gap.gap_id,
                        gap.gap_type,
                        gap.target_node_key,
                        gap.target_option,
                        gap.priority_score,
                    )

        logger.info(
            "classify_gaps session=%s system=%s nodes=%d candidates=%d generated=%d",
            session_id,
            system_id,
            len(nodes),
            len(candidates),
            len(generated),
        )
        return generated

    # ------------------------------------------------------------------
    # Gap detectors
    # ------------------------------------------------------------------

    def _detect_unvisited_announced_options(
        self,
        nodes: dict[str, PromptNode],
        session_id: str,
        system_id: str,
        session_dtmf_pressed: set[str] | None = None,
    ) -> list[GapTask]:
        """UNVISITED_ANNOUNCED_OPTION: announced option with no confirmed edge."""
        tasks: list[GapTask] = []
        # DTMFs pressed this session but not yet linked to edges (next prompt not yet seen)
        pressed_this_session: set[str] = session_dtmf_pressed or set()

        for node_key, node in nodes.items():
            if not _is_menu_node(node):
                continue
            if not node.announced_options:
                continue
            on_transfer_path = _leads_to_transfer(node_key, nodes)
            impact = 0.9 if on_transfer_path else 0.6

            # Confirmed edges: branches with count > 0 OR pressed this session.
            confirmed_options = {
                opt for opt, branch in node.branches.items() if branch.count > 0
            } | pressed_this_session

            for option in node.announced_options:
                # announced_options may be AnnouncedOption objects or strings
                opt_digit = getattr(option, 'dtmf_digit', None) or getattr(option, 'dtmf', None) or str(option)
                if opt_digit in confirmed_options:
                    continue
                score = self._compute_priority(
                    impact_score=impact,
                    age_hours=0.0,          # new gap
                    current_confidence=0.0,  # no traversal yet
                    user_priority=self._default_user_priority,
                    created_at=_now_utc(),
                )
                tasks.append(
                    GapTask(
                        gap_type=GapType.UNVISITED_ANNOUNCED_OPTION,
                        status=GapStatus.PENDING,
                        target_ivr_id=system_id,
                        target_node_key=node_key,
                        target_option=opt_digit,
                        priority_score=score.final_score,
                        score_breakdown=score,
                        operator_priority=self._default_user_priority,
                        source_session_id=session_id,
                        source_engine="discovery",
                    )
                )
        return tasks

    def _detect_unconfirmed_edges(
        self,
        nodes: dict[str, PromptNode],
        session_id: str,
        system_id: str,
    ) -> list[GapTask]:
        """UNCONFIRMED_EDGE: branch traversed exactly once (count == 1)."""
        tasks: list[GapTask] = []
        for node_key, node in nodes.items():
            # Use the parent node's impact as a proxy for the edge's impact.
            on_transfer_path = _leads_to_transfer(node_key, nodes)
            impact = 0.9 if on_transfer_path else 0.6

            for option, branch in node.branches.items():
                if branch.count != 1:
                    continue
                score = self._compute_priority(
                    impact_score=impact,
                    age_hours=0.0,
                    current_confidence=branch.confidence,
                    user_priority=self._default_user_priority,
                    created_at=_now_utc(),
                )
                tasks.append(
                    GapTask(
                        gap_type=GapType.UNCONFIRMED_EDGE,
                        status=GapStatus.PENDING,
                        target_ivr_id=system_id,
                        target_node_key=node_key,
                        target_option=option,
                        priority_score=score.final_score,
                        score_breakdown=score,
                        operator_priority=self._default_user_priority,
                        source_session_id=session_id,
                        source_engine="discovery",
                    )
                )
        return tasks

    def _detect_variable_behavior(
        self,
        nodes: dict[str, PromptNode],
        observations: list[StorageSessionObservation],
        session_id: str,
        system_id: str,
    ) -> list[GapTask]:
        """VARIABLE_BEHAVIOR: node whose prompt_stability_score < 0.6.

        In the current IvrMapper the analogue of prompt_stability_score is the
        node's overall confidence (a running average of STT confidences across
        all observations).  A low confidence indicates the prompt wording
        varies across calls, which is the primary signal of variable behavior.
        """
        tasks: list[GapTask] = []
        for node_key, node in nodes.items():
            if node.confidence >= 0.6:
                continue
            impact = 0.5  # understanding variation, not blocking
            score = self._compute_priority(
                impact_score=impact,
                age_hours=0.0,
                current_confidence=node.confidence,
                user_priority=self._default_user_priority,
                created_at=_now_utc(),
            )
            tasks.append(
                GapTask(
                    gap_type=GapType.VARIABLE_BEHAVIOR,
                    status=GapStatus.PENDING,
                    target_ivr_id=system_id,
                    target_node_key=node_key,
                    target_option=None,
                    priority_score=score.final_score,
                    score_breakdown=score,
                    operator_priority=self._default_user_priority,
                    source_session_id=session_id,
                    source_engine="discovery",
                    observed_confidence=node.confidence,
                )
            )
        return tasks

    def _detect_ambiguous_prompts(
        self,
        observations: list[StorageSessionObservation],
        session_id: str,
        system_id: str,
    ) -> list[GapTask]:
        """AMBIGUOUS_PROMPT: STT confidence < 0.50 for an unconfirmed node."""
        tasks: list[GapTask] = []
        seen_nodes: set[str] = set()  # emit at most one gap per node per session
        for obs in observations:
            if obs.confidence >= 0.50:
                continue
            if obs.is_confirmed:
                continue
            if obs.node_key in seen_nodes:
                continue
            seen_nodes.add(obs.node_key)
            score = self._compute_priority(
                impact_score=0.5,
                age_hours=0.0,
                current_confidence=obs.confidence,
                user_priority=self._default_user_priority,
                created_at=obs.timestamp,
            )
            tasks.append(
                GapTask(
                    gap_type=GapType.AMBIGUOUS_PROMPT,
                    status=GapStatus.PENDING,
                    target_ivr_id=system_id,
                    target_node_key=obs.node_key,
                    target_option=None,
                    priority_score=score.final_score,
                    score_breakdown=score,
                    operator_priority=self._default_user_priority,
                    source_session_id=session_id,
                    source_engine="discovery",
                    observed_confidence=obs.confidence,
                )
            )
        return tasks

    def _detect_timeout_unknowns(
        self,
        nodes: dict[str, PromptNode],
        session_id: str,
        system_id: str,
    ) -> list[GapTask]:
        """TIMEOUT_PATH_UNKNOWN: MENU node with no timeout edge observed.

        A timeout edge is represented by the synthetic DTMF key "" (empty
        string) or by branch keys that contain the word "timeout" or
        "silence".  If none are present, the timeout behavior is unknown.
        """
        _TIMEOUT_KEYS = {"", "timeout", "silence", "no_input"}
        tasks: list[GapTask] = []
        for node_key, node in nodes.items():
            if not _is_menu_node(node):
                continue
            has_timeout_edge = any(
                k.lower() in _TIMEOUT_KEYS or "timeout" in k.lower()
                for k in node.branches
            )
            if has_timeout_edge:
                continue
            score = self._compute_priority(
                impact_score=0.2,   # low priority
                age_hours=0.0,
                current_confidence=node.confidence,
                user_priority=self._default_user_priority,
                created_at=_now_utc(),
            )
            tasks.append(
                GapTask(
                    gap_type=GapType.TIMEOUT_PATH_UNKNOWN,
                    status=GapStatus.PENDING,
                    target_ivr_id=system_id,
                    target_node_key=node_key,
                    target_option=None,
                    priority_score=score.final_score,
                    score_breakdown=score,
                    operator_priority=self._default_user_priority,
                    source_session_id=session_id,
                    source_engine="discovery",
                )
            )
        return tasks

    def _detect_post_auth_unknowns(
        self,
        nodes: dict[str, PromptNode],
        session_id: str,
        system_id: str,
    ) -> list[GapTask]:
        """POST_AUTH_UNKNOWN: AUTH_GATE node with no explored children.

        Auth-gate nodes are detected heuristically by scanning the prompt text
        for authentication keywords.  If such a node has no branches with
        count > 0, its post-auth subtree is entirely unexplored.
        """
        tasks: list[GapTask] = []
        for node_key, node in nodes.items():
            if not _is_auth_gate(node):
                continue
            has_explored = any(b.count > 0 for b in node.branches.values())
            if has_explored:
                continue
            score = self._compute_priority(
                impact_score=0.85,  # high priority; requires human
                age_hours=0.0,
                current_confidence=0.0,
                user_priority=self._default_user_priority,
                created_at=_now_utc(),
            )
            tasks.append(
                GapTask(
                    gap_type=GapType.POST_AUTH_UNKNOWN,
                    status=GapStatus.PENDING,
                    target_ivr_id=system_id,
                    target_node_key=node_key,
                    target_option=None,
                    priority_score=score.final_score,
                    score_breakdown=score,
                    operator_priority=self._default_user_priority,
                    source_session_id=session_id,
                    source_engine="discovery",
                    # Phase 2: auth_credential_ref will be populated when a
                    # credential vault is available.
                    auth_credential_ref=None,
                )
            )
        return tasks

    # ------------------------------------------------------------------
    # Announcement-based hypothesis generation
    # ------------------------------------------------------------------

    def _generate_announcement_hypotheses(
        self,
        nodes: dict[str, PromptNode],
        session_id: str,
        system_id: str,
    ) -> list[GapTask]:
        """HYPOTHESIS_TEST gaps for announced-but-untraversed numeric options.

        When a MENU node announces options up to N but only some have been
        traversed, we emit a HYPOTHESIS_TEST gap for each untraversed option.
        The predicted_value is stored in operator_context; prior_probability
        0.90 is reflected in a high impact_score.
        """
        tasks: list[GapTask] = []
        for node_key, node in nodes.items():
            if not _is_menu_node(node):
                continue
            if not node.announced_options:
                continue

            # Work only with numeric options so we can reason about ranges.
            def _opt_digit(opt) -> str:
                return getattr(opt, 'dtmf_digit', None) or getattr(opt, 'dtmf', None) or str(opt)

            numeric_announced: set[int] = set()
            for opt in node.announced_options:
                try:
                    numeric_announced.add(int(_opt_digit(opt)))
                except ValueError:
                    pass

            if not numeric_announced:
                continue

            max_announced = max(numeric_announced)
            confirmed: set[int] = set()
            for opt, branch in node.branches.items():
                if branch.count > 0:
                    try:
                        confirmed.add(int(opt))
                    except ValueError:
                        pass

            # Generate hypotheses for all announced options not yet confirmed.
            for n in range(1, max_announced + 1):
                if n in confirmed:
                    continue
                score = self._compute_priority(
                    impact_score=0.9,   # announced = very likely exists
                    age_hours=0.0,
                    current_confidence=0.0,
                    user_priority=self._default_user_priority,
                    created_at=_now_utc(),
                )
                tasks.append(
                    GapTask(
                        gap_type=GapType.HYPOTHESIS_TEST,
                        status=GapStatus.PENDING,
                        target_ivr_id=system_id,
                        target_node_key=node_key,
                        target_option=str(n),
                        priority_score=score.final_score,
                        score_breakdown=score,
                        operator_priority=self._default_user_priority,
                        source_session_id=session_id,
                        source_engine="discovery",
                        operator_context=(
                            f"predicted_value: option {n} exists at node {node_key}; "
                            f"prior_probability: 0.90 (announced in menu prompt)"
                        ),
                        operator_label=f"Hypothesis: option {n} @ {node_key[:40]}",
                    )
                )
        return tasks

    # ------------------------------------------------------------------
    # Priority scoring
    # ------------------------------------------------------------------

    def _compute_priority(
        self,
        *,
        impact_score: float,
        age_hours: float,
        current_confidence: float,
        user_priority: float,
        created_at: datetime,
    ) -> PriorityScoreBreakdown:
        """Compute the full priority formula as specified.

        priority_score = (
            0.35 * impact_score
          + 0.25 * urgency_score        # age_hours / 168 capped at 1.0
          + 0.20 * confidence_penalty   # 1.0 - current_confidence
          + 0.15 * user_priority        # default 0.5
          + 0.05 * freshness_bonus      # 1.0 if < 1 hour old, decays to 0
        )
        """
        hours_old = _hours_since(created_at) if age_hours == 0.0 else age_hours
        urgency_score = min(1.0, hours_old / 168.0)   # 168 h = 1 week
        confidence_penalty = max(0.0, 1.0 - current_confidence)
        freshness_bonus = max(0.0, 1.0 - (hours_old / 24.0))

        return PriorityScoreBreakdown(
            impact_score=float(impact_score),
            urgency_score=urgency_score,
            confidence_benefit=confidence_penalty,
            user_priority=float(user_priority),
            freshness_bonus=freshness_bonus,
        )


__all__ = [
    "DiscoveryEngine",
    "StorageBackend",
]
