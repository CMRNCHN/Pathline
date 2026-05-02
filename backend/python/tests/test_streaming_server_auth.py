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


def test_listen_websocket_requires_same_token() -> None:
    server = StreamingServer(stream_auth_token="secret")

    with TestClient(server.app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/listen"):
                pass

        with client.websocket_connect("/listen?stream_token=secret") as websocket:
            websocket.close()
