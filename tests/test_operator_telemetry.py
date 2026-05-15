"""Tests for operator telemetry collection (Agent D1)."""
from __future__ import annotations

from typing import Any

import pytest

from ivr_assessor.backend.routes import telemetry_routes
from ivr_assessor.events.event_bus import bus
from ivr_assessor.events.event_models import OperationalEvent
from ivr_assessor.events.event_types import EventType
from ivr_assessor.events.operator_telemetry import (
    REDACTED_FIELDS,
    record_operator_action,
)


@pytest.fixture
def captured_events() -> list[OperationalEvent]:
    received: list[OperationalEvent] = []

    def _capture(event: OperationalEvent) -> None:
        if event.type == EventType.OPERATOR_ACTION:
            received.append(event)

    bus.subscribe(EventType.OPERATOR_ACTION, _capture)
    try:
        yield received
    finally:
        bus.unsubscribe(EventType.OPERATOR_ACTION, _capture)


def test_operator_telemetry_records_action(captured_events: list[OperationalEvent]) -> None:
    event = record_operator_action(
        "replay_scrubbed",
        context={"from": 0, "to": 5},
        session_id="abc-123",
    )

    assert event.type == EventType.OPERATOR_ACTION
    assert event.payload["action_name"] == "replay_scrubbed"
    assert event.payload["context"] == {"from": 0, "to": 5}
    assert event.meta.session_id == "abc-123"
    assert event.meta.source_component == "operator_telemetry"

    # Verify it actually flowed through the bus.
    assert len(captured_events) == 1
    assert captured_events[0].payload["action_name"] == "replay_scrubbed"


def test_operator_telemetry_redacts_phone_numbers(captured_events: list[OperationalEvent]) -> None:
    event = record_operator_action(
        "dialed_+15555550100",
        context={
            "target": "+15555550100",
            "note": "called 18005551234 from the desk",
            "nested": {"alt": "+447700900000"},
        },
    )

    assert "+15555550100" not in event.payload["action_name"]
    assert "[REDACTED]" in event.payload["action_name"]

    ctx = event.payload["context"]
    assert "+15555550100" not in ctx["target"]
    assert "18005551234" not in ctx["note"]
    assert "+447700900000" not in ctx["nested"]["alt"]
    # Non-phone-number values pass through.
    assert "called" in ctx["note"]


def test_operator_telemetry_redacts_secrets(captured_events: list[OperationalEvent]) -> None:
    event = record_operator_action(
        "config_inspected",
        context={
            "auth_token": "shhh-do-not-share",
            "api_key": "AKIA-very-secret",
            "user_secret": {"inner": "x"},
            "safe_field": "ok-to-see",
            "Password": "hunter2",
        },
    )

    ctx = event.payload["context"]
    assert ctx["auth_token"] == "[REDACTED]"
    assert ctx["api_key"] == "[REDACTED]"
    assert ctx["user_secret"] == "[REDACTED]"
    assert ctx["Password"] == "[REDACTED]"
    assert ctx["safe_field"] == "ok-to-see"

    # Sanity check on the public constant.
    for fragment in ("token", "secret", "key"):
        assert fragment in REDACTED_FIELDS


def test_telemetry_route_endpoint(captured_events: list[OperationalEvent]) -> None:
    response = telemetry_routes.handle_telemetry(
        {
            "action": "export_clicked",
            "context": {"kind": "run_suite", "suiteId": "smoke"},
            "ts": 1700000000.0,
            "session_id": "session-xyz",
        }
    )

    assert response == {"ok": True}
    assert len(captured_events) == 1
    recorded = captured_events[0]
    assert recorded.payload["action_name"] == "export_clicked"
    assert recorded.payload["context"]["suiteId"] == "smoke"
    assert recorded.meta.session_id == "session-xyz"


def test_telemetry_route_rejects_missing_action() -> None:
    with pytest.raises(ValueError):
        telemetry_routes.handle_telemetry({"context": {}})


def test_telemetry_route_rejects_bad_context() -> None:
    with pytest.raises(ValueError):
        telemetry_routes.handle_telemetry({"action": "x", "context": "not-a-dict"})


def test_telemetry_route_accepts_minimal_payload(captured_events: list[OperationalEvent]) -> None:
    response = telemetry_routes.handle_telemetry({"action": "session_started"})
    assert response == {"ok": True}
    assert len(captured_events) == 1
    assert captured_events[0].payload["context"] == {}
    assert captured_events[0].meta.session_id is None


def test_event_type_constant_exists() -> None:
    assert EventType.OPERATOR_ACTION == "OPERATOR_ACTION"


def _flow_through_sink_event(tmp_path) -> dict[str, Any]:
    """Helper: persist an OPERATOR_ACTION through EventSink to disk."""
    from ivr_assessor.events.event_sink import EventSink

    sink = EventSink(base_dir=tmp_path)
    sink.start()
    try:
        event = record_operator_action(
            "replay_scrubbed",
            context={"from": 0, "to": 3},
            session_id="sess-1",
        )
        return event.as_dict()
    finally:
        # EventSink doesn't expose unsubscribe; relying on test isolation by path.
        pass


def test_operator_action_persists_via_existing_event_sink(tmp_path) -> None:
    import json

    data = _flow_through_sink_event(tmp_path)
    assert data["type"] == EventType.OPERATOR_ACTION

    # Find the persisted file by scanning the temp tree.
    written = list(tmp_path.rglob("session_sess-1.jsonl"))
    assert written, "EventSink should have persisted the operator action"
    with open(written[0], "r", encoding="utf-8") as fh:
        line = fh.readline()
    persisted = json.loads(line)
    assert persisted["type"] == EventType.OPERATOR_ACTION
    assert persisted["payload"]["action_name"] == "replay_scrubbed"
    assert persisted["session_id"] == "sess-1"
