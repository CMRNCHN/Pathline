"""Operator telemetry collection (Agent D1).

Captures lightweight operator actions (UI clicks, replay scrubs, session starts)
as OPERATIONAL events on the existing EventBus. This is for *observability* —
the recorded events flow through the standard append-only EventSink and land
in ``~/.ivr_assessor/events/<date>/session_<id>.jsonl``.

Privacy:
    Hard-coded redaction strips phone numbers and credential-shaped fields
    from action names and string values inside the context dict before
    publication. Nested dicts/lists are walked recursively.

Determinism:
    Telemetry publication is one-way — it never mutates replay state or
    blocks the caller. Failures are swallowed (logged) so a misbehaving
    telemetry subscriber cannot break the operator's flow.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from .event_bus import bus
from .event_models import EventMetadata, OperationalEvent
from .event_types import EventType

logger = logging.getLogger(__name__)

# Phone-number-like sequences (optionally prefixed with +). Conservative on
# length to avoid stripping shorter numeric IDs (e.g. offsets).
_PHONE_RE = re.compile(r"\+?\d{10,}")

# Field-name fragments that signal sensitive content. Lowercased substring match.
REDACTED_FIELDS = ("token", "secret", "key", "password", "credential")

_REDACTED_MARKER = "[REDACTED]"


def _looks_sensitive(field_name: str) -> bool:
    """Return True when the field name signals credential-like content."""
    if not field_name:
        return False
    lowered = field_name.lower()
    return any(fragment in lowered for fragment in REDACTED_FIELDS)


def _redact_string(value: str) -> str:
    """Strip phone-number-like substrings from a string value."""
    return _PHONE_RE.sub(_REDACTED_MARKER, value)


def _redact_value(value: Any) -> Any:
    """Recursively redact a context value."""
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, dict):
        return _redact_context(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    return value


def _redact_context(context: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with sensitive fields and phone numbers stripped."""
    cleaned: dict[str, Any] = {}
    for key, value in context.items():
        if _looks_sensitive(str(key)):
            cleaned[key] = _REDACTED_MARKER
            continue
        cleaned[key] = _redact_value(value)
    return cleaned


def record_operator_action(
    action_name: str,
    context: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
    timestamp: Optional[float] = None,
) -> OperationalEvent:
    """Build and publish an OPERATOR_ACTION event.

    Args:
        action_name: Short identifier for the operator action
            (e.g. ``replay_scrubbed``, ``map_saved``).
        context: Arbitrary action-specific metadata. Phone numbers and
            credential-shaped fields are redacted before publication.
        session_id: Optional session this action belongs to. If absent, the
            event lands in the ``unknown_session`` log for the day.
        timestamp: Optional override (test seam); defaults to ``time.time()``.

    Returns:
        The OperationalEvent that was published — useful for tests.
    """
    safe_action = _redact_string(action_name or "unknown_action")
    safe_context = _redact_context(context or {})

    meta_kwargs: dict[str, Any] = {
        "session_id": session_id,
        "source_component": "operator_telemetry",
    }
    if timestamp is not None:
        meta_kwargs["timestamp"] = timestamp

    event = OperationalEvent(
        type=EventType.OPERATOR_ACTION,
        payload={
            "action_name": safe_action,
            "context": safe_context,
        },
        meta=EventMetadata(**meta_kwargs),
    )

    try:
        bus.publish(event)
    except Exception:
        # Telemetry must never break the operator's flow.
        logger.exception("Failed to publish operator telemetry event")

    return event
