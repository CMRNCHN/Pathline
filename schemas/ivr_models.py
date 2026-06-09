"""IVR mapping agent — canonical domain models.

This module is the single source of truth for the IVR epistemic layer.
It defines every dataclass and enum that the IvrMapper, GapTaskQueue,
DiscoveryEngine, ValidationEngine, and HypothesisEngine share.

Companion module: runtime/gap_task.py — defines GapType, GapStatus,
GapTask, and GapTaskQueue. Import those from there; they are not
redefined here.

Confidence decay formula (applies to both structural and content dimensions):

    effective = base * exp(-ln(2) / half_life_hours * delta_hours)

where:
    base             — the best observed confidence (set at last confirmation)
    half_life_hours  — the StabilityClass.half_life_hours for the node
    delta_hours      — (now - last_confirmed).total_seconds() / 3600

All datetimes are timezone-aware UTC. Naive datetimes are rejected at
runtime to prevent clock-arithmetic bugs.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


# ---------------------------------------------------------------------------
# Epistemic state
# ---------------------------------------------------------------------------

class EpistemicState(StrEnum):
    """The agent's belief about how well it understands an IVR node or edge.

    States form a partial order of increasing confidence:
        UNKNOWN < HYPOTHESIZED < EXPLORED_ONCE < CONFIRMED
        AMBIGUOUS (contested — may improve or degrade)
        DEPRECATED (node believed removed; terminal until evidence of return)

    Consumers (GUI, GapTaskQueue, ValidationEngine) use this to decide whether
    to schedule additional visits or treat the node as authoritative.
    """

    UNKNOWN = "unknown"
    """Node/edge has been inferred or hypothesized but never directly observed.
    All confidence values are synthetic (set at construction, not from data)."""

    HYPOTHESIZED = "hypothesized"
    """A hypothesis engine predicted this node/edge exists based on patterns in
    other IVRs or partial structural data. Has not been visited at all."""

    EXPLORED_ONCE = "explored_once"
    """Observed exactly once. Structural confidence is above zero but below the
    multi-observation confirmation floor. Needs a second pass."""

    CONFIRMED = "confirmed"
    """Observed on at least two distinct sessions (or once with very high
    confidence) and the structure has been stable. Default target state."""

    AMBIGUOUS = "ambiguous"
    """Contested: multiple observations produced inconsistent results (different
    next-nodes, different option sets). Requires VARIABLE_BEHAVIOR gap resolution."""

    DEPRECATED = "deprecated"
    """Node/edge is believed to have been removed from the live IVR.
    Unreachable on 2+ consecutive attempts. Not purged from the graph —
    kept as historical record and re-activated if ever observed again."""


# ---------------------------------------------------------------------------
# Stability class
# ---------------------------------------------------------------------------

class StabilityClass(StrEnum):
    """How quickly knowledge about a node decays without fresh observation.

    Higher stability = longer half-life = slower confidence decay.

    Stability is set by the operator or inferred from the node's position in
    the IVR (root menus tend to be static; promotional branches change often).

    Half-life reference:
        STATIC       — 2 160 h  (90 days)  e.g. main menu of a bank IVR
        STABLE       —   720 h  (30 days)  e.g. standard billing / tech support menus
        NORMAL       —   168 h  ( 7 days)  e.g. typical mid-tree nodes
        VOLATILE     —    48 h  ( 2 days)  e.g. promotional, seasonal, time-of-day routing
        EXPERIMENTAL —    12 h  (12 hours) e.g. A/B tested paths, recently added options
    """

    STATIC = "static"
    STABLE = "stable"
    NORMAL = "normal"
    VOLATILE = "volatile"
    EXPERIMENTAL = "experimental"

    @property
    def half_life_hours(self) -> float:
        """Return the confidence half-life in hours for this stability class."""
        _HALF_LIVES: dict[str, float] = {
            "static":       2_160.0,   # 90 days
            "stable":         720.0,   # 30 days
            "normal":         168.0,   #  7 days
            "volatile":        48.0,   #  2 days
            "experimental":    12.0,   # 12 hours
        }
        return _HALF_LIVES[self.value]


# ---------------------------------------------------------------------------
# Node type
# ---------------------------------------------------------------------------

class NodeType(StrEnum):
    """Functional classification of an IVR node.

    Used by the impact-scoring component of GapTask priority: nodes closer
    to HUMAN_HANDOFF or EXTRACTION_POINT receive higher impact scores.

    Consumers that do not understand a value should treat it as UNKNOWN.
    """

    UNKNOWN = "unknown"
    """Type has not been determined yet (default for newly observed nodes)."""

    MENU = "menu"
    """Presents a list of DTMF options to the caller. The most common node
    type. Contains announced_options."""

    INFORMATIONAL = "informational"
    """Plays information (account balance, hold time, etc.) without branching,
    or with a simple 'press any key to continue' prompt."""

    AUTH_GATE = "auth_gate"
    """Requests authentication input (account number, PIN, SSN last 4).
    Subtree behind the gate is POST_AUTH_UNKNOWN until successfully traversed.
    Phase 2 feature — requires credential injection."""

    HUMAN_HANDOFF = "human_handoff"
    """Transfers the call to a live agent. Highest-value endpoint in the graph.
    Nodes within 2 hops of a HUMAN_HANDOFF receive a high impact score."""

    VOICEMAIL = "voicemail"
    """Offers or requires leaving a voicemail. Dead-end for automation."""

    HOLD = "hold"
    """Places the caller on hold pending agent availability. Distinct from
    HUMAN_HANDOFF — the caller has not yet spoken to anyone."""

    EXTRACTION_POINT = "extraction_point"
    """Reads structured data the agent wants to capture (account balance,
    case number, estimated wait time). Phase 2 extraction target."""

    DEAD_END = "dead_end"
    """No outbound options and no data to extract. Terminal path of low value.
    e.g. "We're sorry, our offices are closed" with no further routing."""

    LOOPBACK = "loopback"
    """Returns the caller to a previously visited node (e.g. invalid-input
    retry loops). May indicate a cycle in the graph."""


# ---------------------------------------------------------------------------
# Prompt variants
# ---------------------------------------------------------------------------

@dataclass
class PromptVariant:
    """One observed verbatim rendering of a node's prompt text.

    A single IVR node can produce slightly different audio on different calls
    (variable hold times, A/B wording tests, TTS vs. recorded). Each distinct
    observation is stored as a PromptVariant and the node tracks them all.
    The canonical display text is the longest variant (matching IvrMapper
    heuristic for _ensure_node).

    Consumers: IVRNode.prompt_variants, ValidationEngine (content drift),
    GUI (show all seen wordings).
    """

    text: str
    """Verbatim transcript of this variant."""

    first_observed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this exact wording was first seen."""

    last_observed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this exact wording was most recently seen."""

    observation_count: int = 1
    """How many times this exact wording was observed."""

    session_ids: list[str] = field(default_factory=list)
    """Sessions in which this variant was observed (deduplicated by caller)."""


# ---------------------------------------------------------------------------
# Announced options
# ---------------------------------------------------------------------------

@dataclass
class AnnouncedOption:
    """An option the IVR explicitly announced in a menu prompt.

    Distinct from a BranchObservation (which records actual presses): an
    AnnouncedOption is declared from the prompt text ("Press 1 for billing")
    and exists even if the agent has never pressed that key.

    Consumers: GapTaskQueue (generates UNVISITED_ANNOUNCED_OPTION gaps),
    GUI (renders unexplored branches).
    """

    dtmf: str
    """The DTMF key or sequence announced (e.g. "1", "0", "*", "##")."""

    label: str = ""
    """The purpose as announced by the IVR (e.g. "billing", "technical support").
    Empty if the announcement could not be parsed."""

    first_announced: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this option was first extracted from a prompt."""

    last_announced: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    """When this option was most recently confirmed in a prompt."""

    announcement_count: int = 1
    """How many prompt observations included this option."""

    explored: bool = False
    """True once the agent has pressed this key and recorded the outcome.
    Set by IvrMapper when a BranchObservation is created for this dtmf key."""


# ---------------------------------------------------------------------------
# Confidence decay helpers
# ---------------------------------------------------------------------------

def _decay(base: float, half_life_hours: float, delta_hours: float) -> float:
    """Exponential confidence decay.

    effective = base * exp(-ln(2) / half_life_hours * delta_hours)

    Args:
        base:             Confidence at the time of last confirmation [0.0, 1.0].
        half_life_hours:  Hours until confidence halves (from StabilityClass).
        delta_hours:      Hours elapsed since last confirmation (must be >= 0).

    Returns:
        Effective confidence in [0.0, base]. Never exceeds base.
    """
    if half_life_hours <= 0:
        raise ValueError(f"half_life_hours must be positive, got {half_life_hours}")
    delta = max(0.0, delta_hours)
    return base * math.exp(-math.log(2) / half_life_hours * delta)


def _delta_hours(now: datetime, last_confirmed: datetime) -> float:
    """Return elapsed hours between last_confirmed and now.

    Both arguments must be timezone-aware. Raises TypeError if either is naive.
    Returns 0.0 if now < last_confirmed (clock skew guard).
    """
    if now.tzinfo is None:
        raise TypeError("now must be timezone-aware (use datetime.now(timezone.utc))")
    if last_confirmed.tzinfo is None:
        raise TypeError("last_confirmed must be timezone-aware")
    delta = (now - last_confirmed).total_seconds() / 3600.0
    return max(0.0, delta)


# ---------------------------------------------------------------------------
# IVR node
# ---------------------------------------------------------------------------

@dataclass
class IVRNode:
    """One node in the IVR graph, enriched with epistemic state.

    An IVRNode wraps the raw PromptNode fields from IvrMapper and adds:
    - Epistemic state (how well the agent knows this node)
    - Dual confidence: structural (shape of branches) and content (prompt text)
    - Stability class (controls decay rate)
    - Prompt variant history
    - Announced options from NLP classification

    Primary key: node_key (the normalized prompt key used in IvrMapper._nodes).

    Consumers:
    - IvrMapper: creates and updates IVRNodes during observation
    - GapTaskQueue: reads epistemic_state, confidence, stability_class
    - ValidationEngine: reads prompt_variants for content drift detection
    - GUI: renders node type, epistemic state, and confidence badge
    """

    # -- Identity --
    node_key: str
    """Normalized prompt key (output of _normalize_prompt). Stable across sessions."""

    ivr_id: str = ""
    """Which IVR system this node belongs to (phone number or logical ID)."""

    # -- Display --
    display_prompt: str = ""
    """Canonical display text: the longest observed variant of the prompt.
    Updated by IvrMapper._ensure_node on each new observation."""

    node_type: NodeType = NodeType.UNKNOWN
    """Functional classification. Updated by PromptClassifier after each observation."""

    # -- Epistemic state --
    epistemic_state: EpistemicState = EpistemicState.UNKNOWN
    """Current belief quality. Transitions managed by IvrMapper and ValidationEngine."""

    stability_class: StabilityClass = StabilityClass.NORMAL
    """Decay rate for confidence. Set by operator heuristic or inferred from position."""

    # -- Structural confidence (shape of the branching tree) --
    structural_base: float = 0.0
    """Best-ever structural confidence [0.0, 1.0]. Set on each confirmation."""

    structural_last_confirmed: datetime | None = None
    """When structural_base was last set. None means never confirmed."""

    # -- Content confidence (accuracy of the stored prompt text) --
    content_base: float = 0.0
    """Best-ever content confidence [0.0, 1.0]. Set on each content confirmation."""

    content_last_confirmed: datetime | None = None
    """When content_base was last set. None means never confirmed."""

    # -- Observation history --
    total_observations: int = 0
    """Total number of times this node was reached across all sessions."""

    session_ids: list[str] = field(default_factory=list)
    """Deduplicated list of session IDs in which this node was observed."""

    first_observed: datetime | None = None
    """Timestamp of the first observation of this node."""

    last_observed: datetime | None = None
    """Timestamp of the most recent observation."""

    # -- Prompt variants --
    prompt_variants: list[PromptVariant] = field(default_factory=list)
    """All distinct verbatim wordings observed for this node's prompt.
    The canonical display_prompt is the longest entry here."""

    # -- Announced options --
    announced_options: list[AnnouncedOption] = field(default_factory=list)
    """Options the IVR explicitly announced in this node's prompt.
    Tracked separately from actual branch observations so unexplored options
    are visible even before the agent has pressed those keys."""

    # -- Deprecation tracking --
    consecutive_unreachable: int = 0
    """How many consecutive call attempts failed to reach this node.
    When >= 2, epistemic_state transitions to DEPRECATED."""

    deprecated_at: datetime | None = None
    """When the node was transitioned to DEPRECATED. None if not deprecated."""

    # -- Arbitrary metadata (Phase 2 extension point) --
    metadata: dict[str, Any] = field(default_factory=dict)
    """Unstructured per-node metadata for operator annotations and Phase 2
    features (e.g. extraction config, auth gate credentials)."""

    # ------------------------------------------------------------------ #
    # Confidence methods
    # ------------------------------------------------------------------ #

    def current_structural_confidence(self, now: datetime) -> float:
        """Effective structural confidence at time *now*, after decay.

        Structural confidence reflects how well the agent knows the shape of
        this node's branching tree (which DTMF options exist and where they go).

        Returns 0.0 if structural_last_confirmed is None (never confirmed).
        Confidence decays exponentially according to stability_class.half_life_hours.

        Args:
            now: Current UTC datetime (must be timezone-aware).

        Returns:
            Effective confidence in [0.0, structural_base].
        """
        if self.structural_last_confirmed is None:
            return 0.0
        hours = _delta_hours(now, self.structural_last_confirmed)
        return _decay(self.structural_base, self.stability_class.half_life_hours, hours)

    def current_content_confidence(self, now: datetime) -> float:
        """Effective content confidence at time *now*, after decay.

        Content confidence reflects how accurately the stored prompt text
        matches what the live IVR currently says.

        Returns 0.0 if content_last_confirmed is None (never confirmed).
        Confidence decays exponentially according to stability_class.half_life_hours.

        Args:
            now: Current UTC datetime (must be timezone-aware).

        Returns:
            Effective confidence in [0.0, content_base].
        """
        if self.content_last_confirmed is None:
            return 0.0
        hours = _delta_hours(now, self.content_last_confirmed)
        return _decay(self.content_base, self.stability_class.half_life_hours, hours)

    def effective_confidence(self, now: datetime) -> tuple[float, float]:
        """Return (structural_confidence, content_confidence) at time *now*.

        Convenience wrapper combining both confidence dimensions.

        Args:
            now: Current UTC datetime (must be timezone-aware).

        Returns:
            Tuple of (structural_confidence, content_confidence), each in
            [0.0, 1.0].
        """
        return (
            self.current_structural_confidence(now),
            self.current_content_confidence(now),
        )


# ---------------------------------------------------------------------------
# IVR edge
# ---------------------------------------------------------------------------

@dataclass
class IVREdge:
    """One directed edge in the IVR graph: a DTMF input at a source node
    that leads to a destination node.

    Wraps the BranchObservation fields from IvrMapper and adds epistemic
    enrichment (state, stability, confidence decay).

    Consumers:
    - IvrMapper: creates IVREdges during _observe_action
    - GapTaskQueue: reads epistemic_state and confidence for UNCONFIRMED_EDGE gaps
    - ValidationEngine: detects STRUCTURAL_DRIFT when edge destinations change
    """

    # -- Identity --
    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Stable UUID for this edge. Never changes after creation."""

    source_node_key: str = ""
    """Normalized key of the origin node (IVRNode.node_key)."""

    dtmf: str = ""
    """The DTMF input that traverses this edge (e.g. "1", "0", "*")."""

    destination_node_key: str = ""
    """Normalized key of the destination node (IVRNode.node_key).
    Empty if the destination has not yet been observed (edge is hypothesized)."""

    # -- Epistemic state --
    epistemic_state: EpistemicState = EpistemicState.UNKNOWN
    """Belief quality for this edge specifically."""

    stability_class: StabilityClass = StabilityClass.NORMAL
    """Usually inherits from the source node's stability_class."""

    # -- Observation history --
    observation_count: int = 0
    """How many times this DTMF key was pressed at the source node and the
    destination was observed."""

    session_ids: list[str] = field(default_factory=list)
    """Sessions in which this edge was traversed."""

    first_observed: datetime | None = None
    """Timestamp of the first traversal."""

    last_observed: datetime | None = None
    """Timestamp of the most recent traversal."""

    # -- Confidence (structural dimension only — edges have no content) --
    structural_base: float = 0.0
    """Best observed traversal confidence [0.0, 1.0]."""

    structural_last_confirmed: datetime | None = None
    """When structural_base was last updated."""

    # -- Variable-behavior tracking --
    observed_destinations: list[str] = field(default_factory=list)
    """All distinct destination_node_keys observed. Length > 1 indicates
    VARIABLE_BEHAVIOR (e.g. load balancing, time-of-day routing)."""

    def current_structural_confidence(self, now: datetime) -> float:
        """Effective structural confidence at time *now*, after decay.

        Returns 0.0 if never confirmed.

        Args:
            now: Current UTC datetime (must be timezone-aware).
        """
        if self.structural_last_confirmed is None:
            return 0.0
        hours = _delta_hours(now, self.structural_last_confirmed)
        return _decay(self.structural_base, self.stability_class.half_life_hours, hours)


# ---------------------------------------------------------------------------
# Session observation (immutable event log)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionObservation:
    """Immutable record of a single observation event within a call session.

    SessionObservations are the raw, append-only event log from which
    IvrMapper builds its graph. They are never mutated after creation —
    the epistemic layer derives state from them via IvrMapper rather than
    embedding interpretation in the log itself.

    Consumers:
    - IvrMapper.observe(): primary consumer; builds IVRNodes and IVREdges
    - DiscoveryEngine: scans for UNVISITED_ANNOUNCED_OPTION, UNCONFIRMED_EDGE
    - ValidationEngine: compares against stored node/edge state for drift
    - GUI / operator tooling: raw audit trail for a session

    Frozen dataclass: all fields are set at construction; no mutation is
    possible. Use a new SessionObservation for any corrected re-observation.
    """

    # -- Identity --
    observation_id: str
    """Stable UUID assigned at creation."""

    session_id: str
    """The call session this observation belongs to."""

    ivr_id: str
    """Which IVR system was being mapped."""

    # -- Event --
    event_kind: str
    """One of: 'prompt', 'action', 'timeout', 'hangup', 'error'.
    Matches CallEvent.kind from runtime.state.models."""

    event_text: str
    """The raw text of the event (prompt transcript, DTMF key pressed, etc.)."""

    observed_at: datetime
    """UTC timestamp when the event was captured. Must be timezone-aware."""

    # -- Confidence --
    raw_confidence: float
    """Confidence score assigned by the STT / classification pipeline at
    observation time [0.0, 1.0]. Used to update node/edge confidence via
    IvrMapper._accumulate_confidence."""

    # -- Navigation context --
    sequence_index: int = 0
    """Position of this event within the session's ordered event sequence.
    Used by ValidationEngine to detect non-monotonic ordering."""

    node_key_at_event: str | None = None
    """Normalized key of the IVR node active when this event occurred.
    Set by IvrMapper after processing; None for the first event in a session."""

    # -- Announced options snapshot --
    announced_options_snapshot: tuple[str, ...] = field(default_factory=tuple)
    """Immutable snapshot of the DTMF options announced in this prompt event.
    Only populated for event_kind == 'prompt'. Empty tuple otherwise."""

    # -- Hypothesis linkage (Phase 2) --
    hypothesis_id: str | None = None
    """If this observation was made during a HYPOTHESIS_TEST gap resolution,
    the hypothesis ID is recorded here for provenance tracking."""

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise TypeError(
                f"SessionObservation.observed_at must be timezone-aware; "
                f"got naive datetime {self.observed_at!r} in observation "
                f"{self.observation_id}"
            )
        if not 0.0 <= self.raw_confidence <= 1.0:
            raise ValueError(
                f"raw_confidence must be in [0.0, 1.0], got {self.raw_confidence}"
            )


# ---------------------------------------------------------------------------
# Re-exports for convenience
# ---------------------------------------------------------------------------
# GapType, GapStatus, GapTask, PriorityScoreBreakdown, GapTaskQueue, and the
# transition() function live in runtime.gap_task. Import them from there.
# They are not re-exported here to avoid a circular import (gap_task.py may
# eventually import IVRNode for richer scoring context).
#
# Suggested import pattern for consumers:
#
#   from schemas.ivr_models import (
#       EpistemicState, StabilityClass, NodeType,
#       PromptVariant, AnnouncedOption, IVRNode, IVREdge, SessionObservation,
#   )
#   from runtime.gap_task import GapType, GapStatus, GapTask, GapTaskQueue
