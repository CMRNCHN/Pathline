from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from runtime import sms_server
from runtime.sms_server import AppState, _format_summary, _normalize_number, create_app


@pytest.fixture
def state(tmp_path: Path) -> AppState:
    return AppState(
        allowed={"+15555550001"},
        twilio_sid="ACtest",
        twilio_token="token",
        twilio_number="+15555550000",
        user_phone_number=None,
        public_base_url=None,
        reports_dir=tmp_path,
        validate_signature=False,
    )


@pytest.fixture
def client(state: AppState, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Stub the background worker so /sms doesn't try to dial Twilio.
    async def _noop(state, job):  # noqa: ANN001
        job.status = "done"
        job.summary = {"target_number": job.target, "graph": {}, "events": [], "last_action": None}

    monkeypatch.setattr(sms_server, "_run_mapping_job", _noop)
    return TestClient(create_app(state))


def test_normalize_number_variants() -> None:
    assert _normalize_number("+18005551234") == "+18005551234"
    assert _normalize_number("text 8005551234 please") == "+18005551234"
    assert _normalize_number("call 18005551234") == "+18005551234"
    assert _normalize_number("nope") is None


def test_format_summary_renders_counts() -> None:
    out = _format_summary(
        {
            "target_number": "+18005551234",
            "graph": {"a": {}, "b": {}},
            "events": [{"kind": "prompt"}, {"kind": "dtmf"}],
            "last_action": "press 2",
        }
    )
    assert "+18005551234" in out
    assert "Nodes: 2" in out
    assert "Prompts heard: 1" in out
    assert "press 2" in out


def test_unauthorized_sender_gets_not_authorized(client: TestClient) -> None:
    resp = client.post("/sms", data={"From": "+19999999999", "Body": "+18005551234"})
    assert resp.status_code == 200
    assert "Not authorized" in resp.text


def test_help_message_for_blank_body(client: TestClient) -> None:
    resp = client.post("/sms", data={"From": "+15555550001", "Body": ""})
    assert resp.status_code == 200
    assert "Send a phone number" in resp.text


def test_unparseable_number_rejected(client: TestClient) -> None:
    resp = client.post("/sms", data={"From": "+15555550001", "Body": "hello there"})
    assert resp.status_code == 200
    assert "Couldn't parse" in resp.text


def test_valid_number_enqueues_job(client: TestClient, state: AppState) -> None:
    resp = client.post("/sms", data={"From": "+15555550001", "Body": "+18005551234"})
    assert resp.status_code == 200
    assert "Mapping +18005551234" in resp.text
    assert len(state.jobs) == 1
    job = next(iter(state.jobs.values()))
    assert job.target == "+18005551234"
    assert job.requester == "+15555550001"


def test_status_command(client: TestClient) -> None:
    resp = client.post("/sms", data={"From": "+15555550001", "Body": "status"})
    assert resp.status_code == 200
    assert "No jobs running" in resp.text


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").text == "ok"


def test_signature_validation_rejects_when_enabled(state: AppState) -> None:
    state.validate_signature = True
    app = create_app(state)
    with TestClient(app) as test_client:
        resp = test_client.post("/sms", data={"From": "+15555550001", "Body": "+18005551234"})
        assert resp.status_code == 403


def test_signature_validation_accepts_valid_signature(state: AppState, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("twilio")
    from twilio.request_validator import RequestValidator

    state.validate_signature = True
    state.public_base_url = "http://testserver"

    async def _noop(state, job):  # noqa: ANN001
        job.status = "done"

    monkeypatch.setattr(sms_server, "_run_mapping_job", _noop)

    params = {"From": "+15555550001", "Body": "+18005551234"}
    signature = RequestValidator(state.twilio_token).compute_signature(
        "http://testserver/sms", params
    )

    with TestClient(create_app(state)) as test_client:
        resp = test_client.post(
            "/sms",
            data=params,
            headers={"X-Twilio-Signature": signature},
        )
        assert resp.status_code == 200
        assert "Mapping +18005551234" in resp.text