"""runtime/ivr_mapper.py — IVR graph reconciler.

The IvrMapper receives raw call events and updates the living knowledge graph
stored in StorageBackend. It is the reconciler that turns immutable
SessionObservations into epistemic state transitions on IVRNodes and IVREdges.

Design contract
---------------
- `observe()` is the main entry point during a live call. Every CallEvent
  passes through here and produces an ObservationResult.
- Classification is purely local: exact hash, then Jaccard similarity, then
  keyword overlap. No external calls, no async I/O.
- Epistemic state transitions follow the rules in _apply_state_transition().
  The IvrMapper manages transitions from HYPOTHESIZED → CONFIRMED. The
  DEPRECATED transition is owned by ValidationEngine; this module never writes
  DEPRECATED.
- Gaps detected inside observe() are created immediately and returned in
  ObservationResult.gaps_detected. Deferred gap scoring (classify_gaps) is not
  done here.

Import contract
---------------
  from schemas.ivr_models import (
      EpistemicState, StabilityClass, NodeType,
      PromptVariant, AnnouncedOption, IVRNode, IVREdge,
  )
  from runtime.storage import StorageBackend
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from schemas.ivr_models import (
    AnnouncedOption,
    EpistemicState,
    NodeType,
    StabilityClass,
)
import runtime.storage as _storage_module
from runtime.storage import (
    AnnouncedOption as StorageAnnouncedOption,
    GapTaskRecord,
    IVREdge as StorageIVREdge,
    IVRNode as StorageIVRNode,
    IVRSystem as StorageIVRSystem,
    PromptVariant as StoragePromptVariant,
    Session as StorageSession,
    SessionObservation as StorageSessionObservation,
    StorageBackend,
)

# The storage layer has a coarser EpistemicState enum (UNKNOWN, OBSERVED,
# CONFIRMED, DRIFTED, DEPRECATED). The schemas layer has the richer one used
# by IvrMapper (HYPOTHESIZED, EXPLORED_ONCE, AMBIGUOUS, etc.). We store the
# rich state in node.metadata["rich_epistemic_state"] and map to the coarse
# storage enum for the column value.
_STORAGE_EPISTEMIC = _storage_module.EpistemicState


def _to_storage_epistemic(rich: EpistemicState) -> _STORAGE_EPISTEMIC:
    """Map schemas.EpistemicState → storage.EpistemicState (coarse bucket)."""
    _MAP = {
        EpistemicState.UNKNOWN:       _STORAGE_EPISTEMIC.UNKNOWN,
        EpistemicState.HYPOTHESIZED:  _STORAGE_EPISTEMIC.UNKNOWN,
        EpistemicState.EXPLORED_ONCE: _STORAGE_EPISTEMIC.OBSERVED,
        EpistemicState.CONFIRMED:     _STORAGE_EPISTEMIC.CONFIRMED,
        EpistemicState.AMBIGUOUS:     _STORAGE_EPISTEMIC.DRIFTED,
        EpistemicState.DEPRECATED:    _STORAGE_EPISTEMIC.DEPRECATED,
    }
    return _MAP.get(rich, _STORAGE_EPISTEMIC.UNKNOWN)


def _from_storage_epistemic(coarse: _STORAGE_EPISTEMIC, metadata: dict) -> EpistemicState:
    """Recover the rich EpistemicState from node metadata, falling back to coarse mapping."""
    rich_str = metadata.get("rich_epistemic_state")
    if rich_str:
        try:
            return EpistemicState(rich_str)
        except ValueError:
            pass
    _REVERSE = {
        _STORAGE_EPISTEMIC.UNKNOWN:    EpistemicState.UNKNOWN,
        _STORAGE_EPISTEMIC.OBSERVED:   EpistemicState.EXPLORED_ONCE,
        _STORAGE_EPISTEMIC.CONFIRMED:  EpistemicState.CONFIRMED,
        _STORAGE_EPISTEMIC.DRIFTED:    EpistemicState.AMBIGUOUS,
        _STORAGE_EPISTEMIC.DEPRECATED: EpistemicState.DEPRECATED,
    }
    return _REVERSE.get(coarse, EpistemicState.UNKNOWN)


# ---------------------------------------------------------------------------
# CallEvent — the richer event shape used by IvrMapper
# (distinct from runtime.state.models.CallEvent which is the legacy shape)
# ---------------------------------------------------------------------------

class CallEventType(StrEnum):
    PROMPT_HEARD = "prompt_heard"
    DTMF_INJECTED = "dtmf_injected"
    SPEECH_INJECTED = "speech_injected"
    TRANSFER_DETECTED = "transfer_detected"
    HUMAN_AGENT_REACHED = "human_agent_reached"
    CALL_ENDED = "call_ended"


@dataclass
class CallEvent:
    """Rich call event produced by the telephony layer during a live session.

    This is the input to IvrMapper.observe(). It is distinct from the legacy
    runtime.state.models.CallEvent (which uses kind/text/t_ms). Both coexist
    during the migration to the richer epistemic layer.
    """

    event_type: CallEventType
    timestamp: datetime
    transcript: str | None = None
    """Verbatim STT transcript for PROMPT_HEARD events."""

    audio_ref: str | None = None
    """Opaque reference to the raw audio recording for this event."""

    dtmf_value: str | None = None
    """DTMF digit(s) injected, populated for DTMF_INJECTED events."""

    speech_value: str | None = None
    """Spoken input injected, populated for SPEECH_INJECTED events."""

    stt_confidence: float = 1.0
    """Speech-to-text confidence [0.0, 1.0]. Defaults to 1.0 for injected events."""

    agent_decision: str | None = None
    """The decision label the agent assigned (e.g. 'press:1', 'say:billing').
    Populated for DTMF_INJECTED / SPEECH_INJECTED events."""


# ---------------------------------------------------------------------------
# ObservationResult
# ---------------------------------------------------------------------------

@dataclass
class ObservationResult:
    """The result of processing a single CallEvent through IvrMapper.observe()."""

    observation_id: str
    """Stable UUID for the SessionObservation record created by this call."""

    node_id: str | None
    """The storage node_id matched or created for a PROMPT_HEARD event.
    None when the event type is not PROMPT_HEARD, or when the transcript
    could not be classified (ClassificationResult.match_type == NONE)."""

    epistemic_state_transition: tuple[EpistemicState, EpistemicState] | None
    """(before, after) for nodes whose epistemic state changed. None if the
    state did not change, or if no node was matched."""

    gaps_detected: list[str]
    """gap_ids for GapTaskRecords created immediately during this observation
    (e.g. UNVISITED_ANNOUNCED_OPTION for newly announced options, or
    VARIABLE_BEHAVIOR for an ambiguous destination)."""

    is_new_node: bool
    """True when this observation created a previously-unseen node."""


# ---------------------------------------------------------------------------
# ClassificationResult
# ---------------------------------------------------------------------------

class MatchType(StrEnum):
    EXACT = "exact"
    SEMANTIC = "semantic"
    PARTIAL = "partial"
    NONE = "none"


@dataclass
class ClassificationResult:
    """Result of _classify_prompt for a single transcript."""

    matched_node_id: str | None
    """storage node_id of the best match, or None when match_type is NONE."""

    confidence: float
    """Classification confidence [0.0, 1.0]."""

    match_type: MatchType
    """How the match was achieved."""

    candidates: list[tuple[str, float]]
    """Top-3 (node_id, score) candidates in descending order. May be empty."""


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

_PUNCT_TAIL = re.compile(r"[\s.\,!\?;\:\-—–]+$")
_WHITESPACE = re.compile(r"\s+")
_NON_ALPHA = re.compile(r"[^a-z0-9 ]")


def _normalize_text(text: str) -> str:
    """Canonical key for grouping near-duplicate prompts.

    Collapses whitespace, strips trailing punctuation, lowercases, and removes
    non-alphanumeric characters. Used as the matching surface for all
    classification strategies.
    """
    if not text:
        return ""
    collapsed = _WHITESPACE.sub(" ", text).strip()
    collapsed = _PUNCT_TAIL.sub("", collapsed)
    lowered = collapsed.lower()
    cleaned = _NON_ALPHA.sub(" ", lowered)
    return _WHITESPACE.sub(" ", cleaned).strip()


def _text_hash(text: str) -> str:
    """SHA-256 hash of the normalized text, used for exact matching."""
    normalized = _normalize_text(text)
    return hashlib.sha256(normalized.encode()).hexdigest()


def _word_set(text: str) -> set[str]:
    """Tokenize normalized text into a set of non-empty words."""
    return set(_normalize_text(text).split())


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two word sets. Returns 0.0 if both empty."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _jaccard_distance(a: set[str], b: set[str]) -> float:
    """Jaccard *distance* (1 - similarity). Range [0.0, 1.0]."""
    return 1.0 - _jaccard(a, b)


# ---------------------------------------------------------------------------
# Announced option extraction
# ---------------------------------------------------------------------------

# "Press 1 for billing" / "dial 2 for support" / "enter 0 for operator"
_PRESS_PATTERN = re.compile(
    r"(?:press|dial|enter)\s+(\d+)\s+(?:for|to)\s+([^,\.!?;]+)",
    re.IGNORECASE,
)

# "Say 'billing' or press 1 for billing department"
_SAY_OR_PRESS = re.compile(
    r"say\s+['\"]?([^'\"]+)['\"]?\s+or\s+press\s+(\d+)\s+for\s+([^,\.!?;]+)",
    re.IGNORECASE,
)

# "press 1 through 5 for our menu options" — range shorthand (no label)
_PRESS_RANGE = re.compile(
    r"press\s+(\d+)\s+through\s+(\d+)",
    re.IGNORECASE,
)

# "for X, press N" — with comma
_FOR_PRESS = re.compile(
    r"for\s+([^,]+),\s+press\s+(\d+)",
    re.IGNORECASE,
)
# "for X press N" — no comma (e.g. "For billing press 1")
_FOR_PRESS_NO_COMMA = re.compile(
    r"for\s+((?:a\s+)?[a-z][a-z\s]{1,30}?)\s+press\s+([0-9*#])\b",
    re.IGNORECASE,
)


def _extract_announced_options(transcript: str) -> list[AnnouncedOption]:
    """Parse a PROMPT_HEARD transcript to extract announced DTMF options.

    Handles patterns:
    - "Press 1 for billing. Press 2 for claims."
    - "For billing, press 1. For claims, press 2."
    - "Say 'billing' or press 1 for billing department"
    - "Please press 1 through 5 for our menu options"

    Returns a list of AnnouncedOption objects. The caller is responsible for
    deduplicating against existing options on the node.
    """
    now = datetime.now(timezone.utc)
    results: dict[str, AnnouncedOption] = {}

    for m in _PRESS_PATTERN.finditer(transcript):
        dtmf = m.group(1).strip()
        label = m.group(2).strip().rstrip(" .,")
        if dtmf not in results:
            results[dtmf] = AnnouncedOption(dtmf=dtmf, label=label, first_announced=now, last_announced=now)

    for m in _FOR_PRESS.finditer(transcript):
        label = m.group(1).strip().rstrip(" .,")
        dtmf = m.group(2).strip()
        if dtmf not in results:
            results[dtmf] = AnnouncedOption(dtmf=dtmf, label=label, first_announced=now, last_announced=now)

    for m in _SAY_OR_PRESS.finditer(transcript):
        dtmf = m.group(2).strip()
        label = m.group(3).strip().rstrip(" .,")
        if dtmf not in results:
            results[dtmf] = AnnouncedOption(dtmf=dtmf, label=label, first_announced=now, last_announced=now)

    for m in _FOR_PRESS_NO_COMMA.finditer(transcript):
        label = m.group(1).strip().rstrip(" .,")
        dtmf = m.group(2).strip()
        if dtmf not in results:
            results[dtmf] = AnnouncedOption(dtmf=dtmf, label=label, first_announced=now, last_announced=now)

    for m in _PRESS_RANGE.finditer(transcript):
        lo = int(m.group(1))
        hi = int(m.group(2))
        for n in range(lo, hi + 1):
            dtmf = str(n)
            if dtmf not in results:
                results[dtmf] = AnnouncedOption(dtmf=dtmf, label="", first_announced=now, last_announced=now)

    return list(results.values())


# ---------------------------------------------------------------------------
# Epistemic state transition helpers
# ---------------------------------------------------------------------------

# Confidence values assigned on each transition (per spec)
_CONF_EXPLORED_ONCE = 0.60
_CONF_CONFIRMED_STABLE = 0.90
_CONF_CONFIRMED_STATIC = 0.95
_CONF_AMBIGUOUS = 0.65

# Jaccard distance threshold above which a new observation diverges
_DIVERGENCE_THRESHOLD = 0.20


def _dominant_variant_text(node: StorageIVRNode, storage: StorageBackend) -> str | None:
    """Return the text of the most-seen PromptVariant for this node, or None."""
    variants = storage.get_prompt_variants_for_node(node.node_id) if hasattr(storage, "get_prompt_variants_for_node") else []
    if not variants:
        return node.display_prompt or None
    best = max(variants, key=lambda v: v.seen_count, default=None)
    return best.text if best else node.display_prompt or None


def _base_confidence_for_confirmed(stability: str) -> float:
    """Return the base_confidence to set when a node reaches CONFIRMED state."""
    if stability == StabilityClass.STATIC:
        return _CONF_CONFIRMED_STATIC
    # STABLE, NORMAL, VOLATILE, EXPERIMENTAL all use STABLE threshold
    return _CONF_CONFIRMED_STABLE


# ---------------------------------------------------------------------------
# IvrMapper
# ---------------------------------------------------------------------------

class IvrMapper:
    """Reconciler that turns raw CallEvents into a living IVR knowledge graph.

    The IvrMapper is stateless across sessions: all persistent state lives in
    the StorageBackend. The only in-memory state is an edge-traversal buffer
    that tracks the pending (from_node, trigger) pair within a single session
    until the next PROMPT_HEARD resolves the destination.

    Thread safety: not thread-safe. Each concurrent session should use a
    separate IvrMapper instance or serialize access externally.
    """

    def __init__(self) -> None:
        # Per-session pending edge buffer: session_id -> (from_node_id, trigger, trigger_type)
        self._pending_edge: dict[str, tuple[str, str, str]] = {}
        # Per-session last-seen node: session_id -> node_id
        self._current_node: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def observe(
        self,
        event: CallEvent,
        session_id: str,
        storage: StorageBackend | None = None,
        *,
        branch_confidence: float | None = None,  # deprecated — ignored
    ) -> ObservationResult:
        """Process a single CallEvent and update the world model.

        Args:
            event:      The call event from the telephony layer.
            session_id: The session in which this event occurred.
            storage:    Persistent storage backend.

        Returns:
            ObservationResult with observation_id, matched node_id (or None),
            any epistemic state transition, immediately-created gap_ids, and
            is_new_node flag.
        """
        # Accept the legacy runtime.state.models.CallEvent (kind/text/t_ms) and
        # upcast it to the new shape so old callers don't need to be migrated.
        if not isinstance(event, CallEvent):
            _kind_map = {
                "prompt": CallEventType.PROMPT_HEARD,
                "action": CallEventType.DTMF_INJECTED,
                "dtmf":   CallEventType.DTMF_INJECTED,
                "speech": CallEventType.SPEECH_INJECTED,
                "transfer": CallEventType.TRANSFER_DETECTED,
                "human": CallEventType.HUMAN_AGENT_REACHED,
                "end":   CallEventType.CALL_ENDED,
            }
            _etype = _kind_map.get(getattr(event, "kind", "prompt"), CallEventType.PROMPT_HEARD)
            _t_ms = getattr(event, "t_ms", 0)
            _text = getattr(event, "text", "") or ""
            # Strip "dtmf:" prefix used by legacy callers (e.g. "dtmf:1" → "1")
            _dtmf_raw = getattr(event, "dtmf", None) or (_text if _etype == CallEventType.DTMF_INJECTED else None)
            if _dtmf_raw and _dtmf_raw.startswith("dtmf:"):
                _dtmf_raw = _dtmf_raw[5:]
            event = CallEvent(
                event_type=_etype,
                timestamp=datetime.fromtimestamp(_t_ms / 1000.0, tz=timezone.utc),
                transcript=_text if _etype == CallEventType.PROMPT_HEARD else None,
                dtmf_value=_dtmf_raw,
            )

        if storage is None:
            if not hasattr(self, "_ephemeral_storage"):
                import tempfile
                self._ephemeral_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
                self._ephemeral_db.close()
                self._ephemeral_storage = StorageBackend(self._ephemeral_db.name)
                self._ephemeral_system_id = str(uuid.uuid4())
                self._ephemeral_storage.upsert_ivr_system(StorageIVRSystem(
                    system_id=self._ephemeral_system_id, phone_number="", display_name="ephemeral",
                ))
                self._ephemeral_sessions: set[str] = set()
            storage = self._ephemeral_storage
            if session_id not in self._ephemeral_sessions:
                storage.start_session(StorageSession(
                    session_id=session_id, system_id=self._ephemeral_system_id,
                ))
                self._ephemeral_sessions.add(session_id)

        observation_id = str(uuid.uuid4())
        now = event.timestamp
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Determine the system_id from the session record
        session_record = storage.get_session(session_id)
        system_id = session_record.system_id if session_record else ""

        # Append the raw observation to the immutable log
        raw_payload: dict[str, Any] = {
            "event_type": event.event_type,
            "transcript": event.transcript,
            "dtmf_value": event.dtmf_value,
            "speech_value": event.speech_value,
            "stt_confidence": event.stt_confidence,
            "agent_decision": event.agent_decision,
            "audio_ref": event.audio_ref,
        }
        storage.append_observation(
            StorageSessionObservation(
                obs_id=observation_id,
                session_id=session_id,
                system_id=system_id,
                event_kind=event.event_type,
                event_text=event.transcript or event.dtmf_value or event.speech_value or "",
                t_ms=0,
                confidence=event.stt_confidence,
                observed_at=now,
                raw_payload=raw_payload,
            )
        )

        # Route by event type
        if event.event_type == CallEventType.PROMPT_HEARD:
            return self._handle_prompt(
                event, session_id, system_id, observation_id, now, storage
            )

        if event.event_type in (CallEventType.DTMF_INJECTED, CallEventType.SPEECH_INJECTED):
            return self._handle_input(
                event, session_id, system_id, observation_id, now, storage
            )

        if event.event_type == CallEventType.TRANSFER_DETECTED:
            return self._handle_terminal(
                session_id, system_id, observation_id, NodeType.HUMAN_HANDOFF, storage
            )

        if event.event_type == CallEventType.HUMAN_AGENT_REACHED:
            return self._handle_terminal(
                session_id, system_id, observation_id, NodeType.HUMAN_HANDOFF, storage
            )

        if event.event_type == CallEventType.CALL_ENDED:
            # Clear per-session buffer
            self._pending_edge.pop(session_id, None)
            self._current_node.pop(session_id, None)

        return ObservationResult(
            observation_id=observation_id,
            node_id=None,
            epistemic_state_transition=None,
            gaps_detected=[],
            is_new_node=False,
        )

    # ------------------------------------------------------------------
    # Event-type handlers
    # ------------------------------------------------------------------

    def _handle_prompt(
        self,
        event: CallEvent,
        session_id: str,
        system_id: str,
        observation_id: str,
        now: datetime,
        storage: StorageBackend,
    ) -> ObservationResult:
        transcript = event.transcript or ""
        if not transcript.strip():
            return ObservationResult(
                observation_id=observation_id,
                node_id=None,
                epistemic_state_transition=None,
                gaps_detected=[],
                is_new_node=False,
            )

        # Classify the prompt against known nodes
        classification = self._classify_prompt(transcript, system_id, storage)

        gaps_detected: list[str] = []
        is_new_node = False
        state_transition: tuple[EpistemicState, EpistemicState] | None = None
        node_id: str | None = None

        if classification.match_type == MatchType.NONE or classification.matched_node_id is None:
            # Unknown prompt — create a new node
            new_node = self._create_node(
                transcript=transcript,
                system_id=system_id,
                now=now,
                storage=storage,
            )
            node_id = new_node.node_id
            is_new_node = True
            # New node starts at EXPLORED_ONCE with confidence 0.60
            state_transition = (EpistemicState.UNKNOWN, EpistemicState.EXPLORED_ONCE)
        else:
            node_id = classification.matched_node_id
            storage_node = storage.get_node(node_id)
            if storage_node is None:
                # Defensive: node disappeared between classify and load
                return ObservationResult(
                    observation_id=observation_id,
                    node_id=None,
                    epistemic_state_transition=None,
                    gaps_detected=[],
                    is_new_node=False,
                )

            # Build a PromptVariant for this observation
            variant = StoragePromptVariant(
                variant_id=str(uuid.uuid4()),
                node_id=node_id,
                text=transcript,
                first_seen_at=now,
                last_seen_at=now,
                seen_count=1,
            )
            storage.upsert_prompt_variant(variant)

            # Apply state transition
            coarse = _STORAGE_EPISTEMIC(storage_node.epistemic_state)
            prev_state = _from_storage_epistemic(coarse, storage_node.metadata or {})
            new_state = self._apply_state_transition_to_storage_node(
                storage_node=storage_node,
                new_text=transcript,
                now=now,
                storage=storage,
            )
            meta = dict(storage_node.metadata or {})
            meta["rich_epistemic_state"] = new_state
            if new_state != prev_state:
                state_transition = (prev_state, new_state)
                storage_node.epistemic_state = _to_storage_epistemic(new_state)
                storage_node.confidence = _base_confidence_for_state(new_state, storage_node)
            storage_node.metadata = meta
            storage_node.observation_count += 1
            storage_node.last_seen_at = now
            # Prefer the longest display text
            if len(transcript) > len(storage_node.display_prompt):
                storage_node.display_prompt = transcript
            storage.upsert_node(storage_node)

        # Link observation to node
        storage.link_observation_to_node(observation_id, node_id)

        # Extract and upsert announced options; generate gaps for new ones
        announced = _extract_announced_options(transcript)
        existing_opts = {o.dtmf_digit for o in storage.get_announced_options(node_id)}
        for opt in announced:
            if opt.dtmf not in existing_opts:
                storage.upsert_announced_option(
                    StorageAnnouncedOption(
                        option_id=str(uuid.uuid4()),
                        node_id=node_id,
                        dtmf_digit=opt.dtmf,
                        label_text=opt.label,
                        first_seen_at=now,
                    )
                )
                gap_id = self._create_gap(
                    system_id=system_id,
                    gap_type="unvisited_announced_option",
                    target_node_id=node_id,
                    target_option=opt.dtmf,
                    source_session_id=session_id,
                    now=now,
                    storage=storage,
                )
                gaps_detected.append(gap_id)

        # Close pending edge from previous input event
        if session_id in self._pending_edge:
            from_node_id, trigger, trigger_type = self._pending_edge.pop(session_id)
            self._update_edge(
                from_node_id=from_node_id,
                to_node_id=node_id,
                trigger=trigger,
                trigger_type=trigger_type,
                system_id=system_id,
                now=now,
                storage=storage,
            )

        self._current_node[session_id] = node_id

        return ObservationResult(
            observation_id=observation_id,
            node_id=node_id,
            epistemic_state_transition=state_transition,
            gaps_detected=gaps_detected,
            is_new_node=is_new_node,
        )

    def _handle_input(
        self,
        event: CallEvent,
        session_id: str,
        system_id: str,
        observation_id: str,
        now: datetime,
        storage: StorageBackend,
    ) -> ObservationResult:
        """Handle a DTMF_INJECTED or SPEECH_INJECTED event.

        Records the pending edge from the current node with the injected trigger.
        The destination won't be known until the next PROMPT_HEARD.
        """
        trigger: str
        trigger_type: str

        if event.event_type == CallEventType.DTMF_INJECTED:
            trigger = event.dtmf_value or ""
            trigger_type = "dtmf"
        else:
            trigger = event.speech_value or ""
            trigger_type = "speech"

        current_node_id = self._current_node.get(session_id)
        if current_node_id and trigger:
            self._pending_edge[session_id] = (current_node_id, trigger, trigger_type)

        return ObservationResult(
            observation_id=observation_id,
            node_id=None,
            epistemic_state_transition=None,
            gaps_detected=[],
            is_new_node=False,
        )

    def _handle_terminal(
        self,
        session_id: str,
        system_id: str,
        observation_id: str,
        node_type: NodeType,
        storage: StorageBackend,
    ) -> ObservationResult:
        """Clear pending edge buffer on terminal events (transfer / human agent)."""
        self._pending_edge.pop(session_id, None)
        return ObservationResult(
            observation_id=observation_id,
            node_id=None,
            epistemic_state_transition=None,
            gaps_detected=[],
            is_new_node=False,
        )

    # ------------------------------------------------------------------
    # Prompt classification
    # ------------------------------------------------------------------

    def _classify_prompt(
        self,
        transcript: str,
        system_id: str,
        storage: StorageBackend,
    ) -> ClassificationResult:
        """Classify a prompt transcript against known nodes in *system_id*.

        Strategy (in order):
        1. Exact text hash match against stored PromptVariants (via node's
           display_prompt and known variants).
        2. Jaccard similarity on normalized word sets.
        3. Keyword overlap with known prompt patterns.

        Returns NONE if best score < 0.40.
        """
        if not transcript.strip():
            return ClassificationResult(
                matched_node_id=None,
                confidence=0.0,
                match_type=MatchType.NONE,
                candidates=[],
            )

        target_hash = _text_hash(transcript)
        target_words = _word_set(transcript)
        nodes = storage.get_nodes_by_system(system_id)

        if not nodes:
            return ClassificationResult(
                matched_node_id=None,
                confidence=0.0,
                match_type=MatchType.NONE,
                candidates=[],
            )

        # --- Strategy 1: exact hash ---
        for node in nodes:
            if _text_hash(node.display_prompt) == target_hash:
                return ClassificationResult(
                    matched_node_id=node.node_id,
                    confidence=1.0,
                    match_type=MatchType.EXACT,
                    candidates=[(node.node_id, 1.0)],
                )
            # Also check stored prompt variants
            if hasattr(storage, "get_prompt_variants_for_node"):
                for variant in storage.get_prompt_variants_for_node(node.node_id):
                    if _text_hash(variant.text) == target_hash:
                        return ClassificationResult(
                            matched_node_id=node.node_id,
                            confidence=1.0,
                            match_type=MatchType.EXACT,
                            candidates=[(node.node_id, 1.0)],
                        )

        # --- Strategy 2: Jaccard similarity ---
        scores: list[tuple[str, float]] = []
        for node in nodes:
            node_words = _word_set(node.display_prompt)
            score = _jaccard(target_words, node_words)
            scores.append((node.node_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        top3 = scores[:3]

        if top3 and top3[0][1] >= 0.40:
            best_id, best_score = top3[0]
            # Distinguish SEMANTIC (high) from PARTIAL (moderate)
            match_type = MatchType.SEMANTIC if best_score >= 0.65 else MatchType.PARTIAL
            return ClassificationResult(
                matched_node_id=best_id,
                confidence=best_score,
                match_type=match_type,
                candidates=top3,
            )

        # --- Strategy 3: keyword overlap ---
        kw_scores: list[tuple[str, float]] = []
        for node in nodes:
            node_words = _word_set(node.display_prompt)
            if not node_words:
                continue
            overlap = len(target_words & node_words) / len(node_words)
            kw_scores.append((node.node_id, overlap))

        kw_scores.sort(key=lambda x: x[1], reverse=True)
        top3_kw = kw_scores[:3]

        if top3_kw and top3_kw[0][1] >= 0.40:
            best_id, best_score = top3_kw[0]
            return ClassificationResult(
                matched_node_id=best_id,
                confidence=best_score,
                match_type=MatchType.PARTIAL,
                candidates=top3_kw,
            )

        return ClassificationResult(
            matched_node_id=None,
            confidence=top3[0][1] if top3 else 0.0,
            match_type=MatchType.NONE,
            candidates=top3,
        )

    # ------------------------------------------------------------------
    # Epistemic state transitions
    # ------------------------------------------------------------------

    def _apply_state_transition_to_storage_node(
        self,
        storage_node: StorageIVRNode,
        new_text: str,
        now: datetime,
        storage: StorageBackend,
    ) -> EpistemicState:
        """Compute the next epistemic state for a node given a new observation.

        Rules (IvrMapper owns transitions from HYPOTHESIZED through AMBIGUOUS;
        DEPRECATED is owned by ValidationEngine):

          hypothesized  → explored_once:  first successful observe() visit
          explored_once → confirmed:      second visit where Jaccard distance <= 0.20
          confirmed     → ambiguous:      third+ visit where new variant diverges > 0.20
          confirmed/ambiguous → deprecated: set by ValidationEngine, never here

        Args:
            storage_node: The mutable StorageIVRNode being updated.
            new_text:     The verbatim transcript from this observation.
            now:          Current UTC datetime.
            storage:      StorageBackend (for variant lookup).

        Returns:
            The new EpistemicState (may be the same as the current state).
        """
        coarse = _STORAGE_EPISTEMIC(storage_node.epistemic_state)
        current = _from_storage_epistemic(coarse, storage_node.metadata or {})

        if current == EpistemicState.DEPRECATED:
            # If a deprecated node is observed again, resurface it as explored_once.
            return EpistemicState.EXPLORED_ONCE

        if current in (EpistemicState.UNKNOWN, EpistemicState.HYPOTHESIZED):
            return EpistemicState.EXPLORED_ONCE

        if current == EpistemicState.EXPLORED_ONCE:
            # Transition to CONFIRMED if new text is within 20% Jaccard distance
            # of the dominant (existing) display prompt.
            dominant = storage_node.display_prompt or ""
            distance = _jaccard_distance(_word_set(new_text), _word_set(dominant))
            if distance <= _DIVERGENCE_THRESHOLD:
                return EpistemicState.CONFIRMED
            # Text diverged; stay at EXPLORED_ONCE to collect more data.
            return EpistemicState.EXPLORED_ONCE

        if current == EpistemicState.CONFIRMED:
            dominant = storage_node.display_prompt or ""
            distance = _jaccard_distance(_word_set(new_text), _word_set(dominant))
            if distance > _DIVERGENCE_THRESHOLD:
                return EpistemicState.AMBIGUOUS
            return EpistemicState.CONFIRMED

        if current == EpistemicState.AMBIGUOUS:
            # Stays AMBIGUOUS; ValidationEngine decides if it improves.
            return EpistemicState.AMBIGUOUS

        return current

    # ------------------------------------------------------------------
    # Node creation
    # ------------------------------------------------------------------

    def _create_node(
        self,
        transcript: str,
        system_id: str,
        now: datetime,
        storage: StorageBackend,
    ) -> StorageIVRNode:
        """Create and persist a new IVRNode for an unrecognized prompt.

        The new node starts at EXPLORED_ONCE with base_confidence 0.60.
        """
        node_id = str(uuid.uuid4())
        canonical_key = _normalize_text(transcript)

        node = StorageIVRNode(
            node_id=node_id,
            system_id=system_id,
            canonical_key=canonical_key,
            display_prompt=transcript,
            epistemic_state=_to_storage_epistemic(EpistemicState.EXPLORED_ONCE),
            confidence=_CONF_EXPLORED_ONCE,
            observation_count=1,
            first_seen_at=now,
            last_seen_at=now,
            metadata={"rich_epistemic_state": EpistemicState.EXPLORED_ONCE},
        )
        storage.upsert_node(node)

        # Persist initial prompt variant
        storage.upsert_prompt_variant(
            StoragePromptVariant(
                variant_id=str(uuid.uuid4()),
                node_id=node_id,
                text=transcript,
                first_seen_at=now,
                last_seen_at=now,
                seen_count=1,
            )
        )
        return node

    # ------------------------------------------------------------------
    # Edge updates
    # ------------------------------------------------------------------

    def _update_edge(
        self,
        from_node_id: str,
        to_node_id: str,
        trigger: str,
        trigger_type: str,
        system_id: str,
        now: datetime,
        storage: StorageBackend,
    ) -> None:
        """Update or create an IVREdge for a completed traversal.

        Epistemic state rules:
        - First traversal:                  explored_once, confidence = 0.65
        - Second consistent traversal:      confirmed,     confidence = 0.90
        - Additional consistent traversals: stay confirmed, confidence unchanged
        - Failed traversal (unexpected dest): consecutive_failures += 1 (tracked
          in edge metadata; ValidationEngine handles degradation)

        Args:
            from_node_id:  Storage node_id of the source node.
            to_node_id:    Storage node_id of the destination node.
            trigger:       The DTMF or speech value that caused the traversal.
            trigger_type:  "dtmf" or "speech".
            system_id:     The IVR system.
            now:           Current UTC datetime.
            storage:       StorageBackend.
        """
        # Load existing edges from this source node
        existing_edges = storage.get_edges_from_node(from_node_id)

        # Find matching edge by trigger (dtmf_option)
        matching: StorageIVREdge | None = None
        for edge in existing_edges:
            if edge.dtmf_option == trigger:
                matching = edge
                break

        if matching is None:
            # First traversal: create at explored_once
            edge = StorageIVREdge(
                edge_id=str(uuid.uuid4()),
                system_id=system_id,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                dtmf_option=trigger,
                observation_count=1,
                confidence=0.65,
                first_seen_at=now,
                last_seen_at=now,
                metadata={
                    "epistemic_state": EpistemicState.EXPLORED_ONCE,
                    "trigger_type": trigger_type,
                    "observed_destinations": [to_node_id],
                    "consecutive_failures": 0,
                },
            )
            storage.upsert_edge(edge)
        else:
            obs_count = matching.observation_count + 1
            meta = dict(matching.metadata) if matching.metadata else {}
            observed_dests: list[str] = meta.get("observed_destinations", [matching.to_node_id])

            # Determine if destination is consistent
            if to_node_id not in observed_dests:
                observed_dests.append(to_node_id)
                meta["consecutive_failures"] = meta.get("consecutive_failures", 0) + 1
                # Variable behavior — keep existing epistemic state
            else:
                meta["consecutive_failures"] = 0

            # State promotion: explored_once → confirmed on second consistent traversal
            current_state_str = meta.get("epistemic_state", EpistemicState.EXPLORED_ONCE)
            current_state = EpistemicState(current_state_str)
            new_confidence = matching.confidence
            new_state = current_state

            if current_state == EpistemicState.EXPLORED_ONCE and len(observed_dests) == 1:
                # Second+ consistent traversal
                if obs_count >= 2:
                    new_state = EpistemicState.CONFIRMED
                    new_confidence = 0.90
            elif current_state == EpistemicState.CONFIRMED and len(observed_dests) > 1:
                new_state = EpistemicState.AMBIGUOUS

            meta["epistemic_state"] = new_state
            meta["observed_destinations"] = observed_dests
            meta["trigger_type"] = trigger_type

            updated = StorageIVREdge(
                edge_id=matching.edge_id,
                system_id=system_id,
                from_node_id=from_node_id,
                to_node_id=to_node_id,
                dtmf_option=trigger,
                observation_count=obs_count,
                confidence=new_confidence,
                first_seen_at=matching.first_seen_at,
                last_seen_at=now,
                metadata=meta,
            )
            storage.upsert_edge(updated)

    # ------------------------------------------------------------------
    # Gap creation
    # ------------------------------------------------------------------

    def _create_gap(
        self,
        system_id: str,
        gap_type: str,
        target_node_id: str | None,
        target_option: str | None,
        source_session_id: str | None,
        now: datetime,
        storage: StorageBackend,
    ) -> str:
        """Create and persist a GapTaskRecord. Returns the new gap_id."""
        gap_id = str(uuid.uuid4())
        gap = GapTaskRecord(
            gap_id=gap_id,
            system_id=system_id,
            gap_type=gap_type,
            status="pending",
            priority_score=0.5,
            target_node_id=target_node_id,
            target_option=target_option,
            source_session_id=source_session_id,
            source_engine="ivr_mapper",
            created_at=now,
            updated_at=now,
        )
        storage.push_gap(gap)
        return gap_id

    # ------------------------------------------------------------------
    # Graph snapshot
    # ------------------------------------------------------------------

    def graph(
        self,
        system_id: str | None = None,
        storage: StorageBackend | None = None,
    ) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the IVR graph for *system_id*.

        Schema::

            {
              "nodes": {
                "<node_id>": {
                  "node_id": str,
                  "display_prompt": str,
                  "epistemic_state": str,
                  "confidence": float,
                  "observation_count": int,
                  "announced_options": [
                    {"dtmf": str, "label": str}
                  ],
                }
              },
              "edges": {
                "<edge_id>": {
                  "edge_id": str,
                  "from_node_id": str,
                  "to_node_id": str,
                  "trigger": str,
                  "observation_count": int,
                  "confidence": float,
                  "epistemic_state": str,
                }
              },
              "gaps": {
                "<gap_id>": {
                  "gap_id": str,
                  "gap_type": str,
                  "status": str,
                  "target_node_id": str | null,
                  "target_option": str | null,
                  "priority_score": float,
                }
              }
            }

        Args:
            system_id: The IVR system whose graph to snapshot.
            storage:   StorageBackend holding the persisted state.

        Returns:
            A plain dict suitable for json.dumps().
        """
        _using_defaults = storage is None and system_id is None
        if storage is None:
            storage = getattr(self, "_ephemeral_storage", None) or StorageBackend(":memory:")
        if system_id is None:
            system_id = getattr(self, "_ephemeral_system_id", "")

        # Legacy callers (no args) expect {prompt_text: {observations, sessions, branches, ...}}
        if _using_defaults:
            return self._legacy_graph(system_id, storage)

        nodes: dict[str, Any] = {}
        edges: dict[str, Any] = {}
        gaps: dict[str, Any] = {}

        for node in storage.get_nodes_by_system(system_id):
            opts = [
                {"dtmf": o.dtmf_digit, "label": o.label_text}
                for o in storage.get_announced_options(node.node_id)
            ]
            rich_state = _from_storage_epistemic(
                _STORAGE_EPISTEMIC(node.epistemic_state),
                node.metadata or {},
            )
            nodes[node.node_id] = {
                "node_id": node.node_id,
                "display_prompt": node.display_prompt,
                "epistemic_state": str(rich_state),
                "confidence": round(node.confidence, 6),
                "observation_count": node.observation_count,
                "first_seen_at": node.first_seen_at.isoformat() if node.first_seen_at else None,
                "last_seen_at": node.last_seen_at.isoformat() if node.last_seen_at else None,
                "announced_options": sorted(opts, key=lambda o: _option_sort_key(o["dtmf"])),
            }

        # Collect edges for all nodes in this system
        for node_id in list(nodes):
            for edge in storage.get_edges_from_node(node_id):
                meta = edge.metadata or {}
                edges[edge.edge_id] = {
                    "edge_id": edge.edge_id,
                    "from_node_id": edge.from_node_id,
                    "to_node_id": edge.to_node_id,
                    "trigger": edge.dtmf_option,
                    "observation_count": edge.observation_count,
                    "confidence": round(edge.confidence, 6),
                    "epistemic_state": str(meta.get("epistemic_state", EpistemicState.UNKNOWN)),
                    "trigger_type": meta.get("trigger_type", "dtmf"),
                    "consecutive_failures": meta.get("consecutive_failures", 0),
                    "observed_destinations": meta.get("observed_destinations", []),
                }

        # Collect pending gaps for this system
        for gap in storage.get_pending_gaps(system_id):
            gaps[gap.gap_id] = {
                "gap_id": gap.gap_id,
                "gap_type": gap.gap_type,
                "status": gap.status,
                "target_node_id": gap.target_node_id,
                "target_option": gap.target_option,
                "priority_score": round(gap.priority_score, 6),
            }

        return {"nodes": nodes, "edges": edges, "gaps": gaps}

    def _legacy_graph(self, system_id: str, storage: StorageBackend) -> dict[str, Any]:
        """Return the pre-refactor graph shape: {prompt_text: {observations, ...}}."""
        raw_nodes = storage.get_nodes_by_system(system_id)
        prompt_by_id: dict[str, str] = {n.node_id: n.display_prompt for n in raw_nodes}

        # Build branch counts from resolved edges in storage
        result: dict[str, Any] = {}
        for node in raw_nodes:
            obs_records = storage.get_observations_for_node(node.node_id)
            sessions = sorted({o.session_id for o in obs_records if o.session_id})
            opts = sorted(o.dtmf_digit for o in storage.get_announced_options(node.node_id))
            branches: dict[str, Any] = {}
            for edge in storage.get_edges_from_node(node.node_id):
                dest_prompt = prompt_by_id.get(edge.to_node_id, edge.to_node_id)
                branches[edge.dtmf_option] = {
                    "count": edge.observation_count,
                    "confidence": round(edge.confidence, 6),
                    "sessions": [],
                    "next_prompts": [dest_prompt] if dest_prompt else [],
                }
            result[node.display_prompt] = {
                "observations": node.observation_count,
                "confidence": round(node.confidence, 6),
                "sessions": sessions,
                "announced_options": opts,
                "branches": branches,
            }

        # Fold in unresolved pending edges (DTMF pressed but no follow-up prompt yet)
        for session_id, (from_node_id, trigger, _trigger_type) in self._pending_edge.items():
            from_prompt = prompt_by_id.get(from_node_id)
            if from_prompt and from_prompt in result:
                br = result[from_prompt]["branches"]
                if trigger in br:
                    br[trigger]["count"] += 1
                    br[trigger]["sessions"] = sorted(set(br[trigger]["sessions"]) | {session_id})
                else:
                    br[trigger] = {
                        "count": 1,
                        "confidence": 0.0,
                        "sessions": [session_id],
                        "next_prompts": [],
                    }

        return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _base_confidence_for_state(
    state: EpistemicState,
    node: StorageIVRNode,
) -> float:
    """Return the base_confidence to assign when entering *state*."""
    if state == EpistemicState.EXPLORED_ONCE:
        return _CONF_EXPLORED_ONCE
    if state == EpistemicState.CONFIRMED:
        # Use STATIC confidence for nodes whose metadata marks them static
        stability = node.metadata.get("stability_class", StabilityClass.STABLE)
        if stability == StabilityClass.STATIC:
            return _CONF_CONFIRMED_STATIC
        return _CONF_CONFIRMED_STABLE
    if state == EpistemicState.AMBIGUOUS:
        return _CONF_AMBIGUOUS
    if state == EpistemicState.HYPOTHESIZED:
        return 0.30
    return 0.0


def _option_sort_key(dtmf: str) -> tuple[int, str]:
    """Natural sort: numerics before non-numerics, within numerics by value."""
    try:
        return (0, f"{int(dtmf):020d}")
    except ValueError:
        return (1, dtmf)


# ---------------------------------------------------------------------------
# Legacy compatibility shim
# ---------------------------------------------------------------------------
# The pre-refactor IvrMapper used a simpler API:
#     observe(event: CallEvent, branch_confidence: float, session_id: str)
# where CallEvent had kind/text/t_ms fields. The new IvrMapper.observe()
# takes (event: CallEvent, session_id: str, storage: StorageBackend).
#
# The legacy API is NOT preserved in this class. Callers using the old shape
# must migrate to the new StorageBackend-backed observe() call.
# The legacy _normalize_prompt, BranchObservation, PromptNode, _SessionState,
# branch_sort_key, _branch_sort_key, and _accumulate_confidence names are
# available from this module for any callers that imported them directly;
# they are re-exported as private aliases below to avoid breaking those imports
# during the migration window.

def _normalize_prompt(text: str) -> str:
    """Alias for _normalize_text; retained for migration compatibility."""
    return _normalize_text(text)


def branch_sort_key(dtmf: str) -> tuple[int, str]:
    """Sort key for DTMF branch labels. Numerics before non-numerics, then by value."""
    return _option_sort_key(dtmf)
