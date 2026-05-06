import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ivr_assessor.streaming_server import StreamingServer, append_stream_auth_token


def test_stream_url_auth_token_is_appended_once() -> None:
    assert (
        append_stream_auth_token("wss://example.ngrok-free.app/stream", "secret")
        == "wss://example.ngrok-free.app/stream?token=secret"
    )
    # If a URL already has a token, it should be replaced with the current one
    # (handles the case where the server restarted with a new token)
    assert (
        append_stream_auth_token("wss://example.ngrok-free.app/stream?token=old", "secret")
        == "wss://example.ngrok-free.app/stream?token=secret"
    )


def test_stream_websocket_rejects_missing_token() -> None:
    server = StreamingServer(stream_auth_token="secret")

    with TestClient(server.app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/stream"):
                pass


def test_stream_websocket_accepts_valid_token() -> None:
    server = StreamingServer(stream_auth_token="secret")

    with TestClient(server.app) as client:
        with client.websocket_connect("/stream?token=secret") as websocket:
            websocket.send_text(json.dumps({"event": "stop"}))


def test_recording_status_ignores_non_completed() -> None:
    server = StreamingServer(stream_auth_token="secret")
    with TestClient(server.app) as client:
        resp = client.post("/recording-status", data={"RecordingStatus": "in-progress"})
        assert resp.status_code == 204


def test_recording_status_completed_returns_200() -> None:
    server = StreamingServer(stream_auth_token="secret")
    statuses: list[str] = []
    server.register_status_callback(statuses.append)

    with TestClient(server.app) as client:
        resp = client.post(
            "/recording-status",
            data={
                "RecordingStatus": "completed",
                "RecordingUrl": "https://api.twilio.com/recordings/RE123",
                "RecordingSid": "RE123",
                "CallSid": "CA456",
            },
        )
    assert resp.status_code == 200
    assert any("RE123" in s for s in statuses)


def test_listen_websocket_requires_same_token() -> None:
    server = StreamingServer(stream_auth_token="secret")

    with TestClient(server.app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/listen"):
                pass

        with client.websocket_connect("/listen?stream_token=secret") as websocket:
            websocket.close()
