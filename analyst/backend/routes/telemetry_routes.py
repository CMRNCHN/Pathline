"""Operator telemetry route handlers (Agent D1).

Receives ``POST /api/telemetry`` from the frontend, validates the payload,
and forwards to ``record_operator_action`` which publishes through the
existing EventBus. The append-only EventSink persists the event to the
standard session JSONL log — no new storage backend.

Request shape::

    {"action": "replay_scrubbed", "context": {...}, "ts": 1700000000.0,
     "session_id": "abc"}

Both ``context`` and ``session_id`` are optional. ``ts`` is informational —
the backend timestamp is authoritative.
"""
from __future__ import annotations

from typing import Any

from ...events.operator_telemetry import record_operator_action


def handle_telemetry(data: dict[str, Any]) -> dict[str, Any]:
    """Handle a POST /api/telemetry request.

    Raises:
        ValueError: when ``action`` is missing or empty.
    """
    if not isinstance(data, dict):
        raise ValueError("telemetry payload must be a JSON object")

    action = data.get("action")
    if not action or not isinstance(action, str):
        raise ValueError("telemetry payload missing required 'action' field")

    context = data.get("context") or {}
    if not isinstance(context, dict):
        raise ValueError("telemetry 'context' must be an object when provided")

    session_id = data.get("session_id")
    if session_id is not None and not isinstance(session_id, str):
        raise ValueError("telemetry 'session_id' must be a string when provided")

    record_operator_action(
        action_name=action,
        context=context,
        session_id=session_id,
    )

    return {"ok": True}
