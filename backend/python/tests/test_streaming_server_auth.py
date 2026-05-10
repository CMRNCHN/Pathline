import json
import base64

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ivr_assessor.backend.ui.ui_state import AppState, QueuePromptSource
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


def test_runtime_metrics_endpoint_returns_payload() -> None:
    server = StreamingServer(stream_auth_token="secret")
    with TestClient(server.app) as client:
        resp = client.get("/runtime-metrics")
    assert resp.status_code == 200
    payload = resp.json()
    assert "last_stream_metrics" in payload
    assert payload["stream_auth_token_configured"] is True
    assert "lifecycle_events" in payload


class _FakeTranscriber:
    INPUT_FORMAT = "mulaw_8k"

    def __init__(self) -> None:
        self._closed = False
        self._audio_chunks: list[int] = []

    async def connect(self) -> bool:
        return True

    async def process_audio(self, audio_bytes: bytes) -> None:
        self._audio_chunks.append(len(audio_bytes))

    async def close(self) -> None:
        self._closed = True

    def stats(self) -> dict[str, object]:
        return {
            "backend": "fake",
            "connected": True,
            "queue_size": 0,
            "max_queue_size_seen": 0,
            "chunks_seen": len(self._audio_chunks),
            "closed": self._closed,
        }


def test_runtime_metrics_capture_lifecycle_and_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    import ivr_assessor.stt_service as stt_service

    monkeypatch.setattr(
        stt_service,
        "create_transcriber",
        lambda on_transcript=None, on_status=None: _FakeTranscriber(),
    )

    server = StreamingServer(stream_auth_token="secret")
    media_payload = base64.b64encode(bytes([0xFF] * 160)).decode("ascii")

    with TestClient(server.app) as client:
        server.register_transcript_callback(lambda text, is_final, speech_final: None)
        server.register_status_callback(lambda status: None)

        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/stream"):
                pass

        with client.websocket_connect("/listen?stream_token=secret") as websocket:
            websocket.close()

        with client.websocket_connect("/stream?token=secret") as websocket:
            websocket.send_text(json.dumps({"event": "connected"}))
            websocket.send_text(
                json.dumps({"event": "start", "start": {"streamSid": "MZ123", "callSid": "CA123"}})
            )
            websocket.send_text(json.dumps({"event": "media", "media": {"payload": media_payload}}))
            websocket.send_text(json.dumps({"event": "stop"}))

        server.clear_callbacks()
        payload = client.get("/runtime-metrics").json()

    assert payload["callbacks_registered"] == 0
    assert payload["status_callbacks_registered"] == 0
    assert payload["callbacks_cleared_count"] >= 1
    assert any(
        event["endpoint"] == "/stream" and event["phase"] == "rejected_unauthorized"
        for event in payload["lifecycle_events"]
    )
    assert any(
        event["endpoint"] == "/listen" and event["phase"] == "accepted"
        for event in payload["lifecycle_events"]
    )
    assert any(
        event["endpoint"] == "/stream" and event["phase"] == "start_event"
        for event in payload["lifecycle_events"]
    )
    assert payload["last_stream_metrics"]["last_event"] == "stop"
    assert payload["last_stream_metrics"]["media_bytes_received"] == 160
    assert payload["last_stream_metrics"]["transcriber_stats"]["chunks_seen"] == 1


def test_app_state_checkpoints_and_queue_metrics_are_deterministic() -> None:
    state = AppState()
    state.begin_startup_trace()
    state.record_runtime_checkpoint("launch.begin", "test launch", category="startup")
    state.record_cleanup_event("cleanup.begin", "test cleanup")
    snapshot = state.runtime_checkpoint_snapshot()

    assert snapshot["launch_sequence"] == 1
    assert snapshot["checkpoint_count"] == 2
    assert snapshot["cleanup_count"] == 1
    assert snapshot["last_checkpoint"]["stage"] == "cleanup.begin"

    source = QueuePromptSource()
    source.prompt_queue.put("hello world")
    before = source.metrics()
    assert before["current_depth"] == 1
    assert before["puts_total"] == 1
    assert before["max_depth_seen"] == 1

    event = source.next_event("session-1")
    after = source.metrics()
    assert event.text == "hello world"
    assert after["current_depth"] == 0
    assert after["gets_total"] == 1

    state.reset()
    reset_snapshot = state.runtime_checkpoint_snapshot()
    assert reset_snapshot["reset_count"] == 1
    assert reset_snapshot["last_checkpoint"]["stage"] == "state.reset"
