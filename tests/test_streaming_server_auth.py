import json
import base64

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import analyst.backend.live_map_gui as live_map_gui
from analyst.backend.ui.ui_state import AppState, QueuePromptSource
from runtime.transport.streaming_server import StreamingServer, append_stream_auth_token


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
    import runtime.media.stt_service as stt_service

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


def test_simulated_transcript_flow_smoke_covers_filter_queue_and_runtime_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STT_BACKEND", "simulated")

    state = AppState()
    state.begin_startup_trace()
    state.record_runtime_checkpoint(
        "session.stream_callbacks_registered",
        "simulated transcript probe",
        category="session",
    )
    state.is_running = True
    state.start_time = 1.0
    source = QueuePromptSource()
    state.source = source

    server = StreamingServer(stream_auth_token="secret")
    monkeypatch.setattr(live_map_gui, "STATE", state)
    monkeypatch.setattr(live_map_gui, "_persistent_stream", server)

    on_transcript, on_status = live_map_gui._build_stream_callbacks(source=source, state=state)
    server.register_transcript_callback(on_transcript)
    server.register_status_callback(on_status)

    media_payload = base64.b64encode(bytes([0xFF] * 160)).decode("ascii")
    with TestClient(server.app) as client:
        with client.websocket_connect("/stream?token=secret") as websocket:
            websocket.send_text(json.dumps({"event": "connected"}))
            websocket.send_text(
                json.dumps({"event": "start", "start": {"streamSid": "MZSIM", "callSid": "CASIM"}})
            )
            for _ in range(250):
                websocket.send_text(json.dumps({"event": "media", "media": {"payload": media_payload}}))
            websocket.send_text(json.dumps({"event": "stop"}))

        stream_payload = client.get("/runtime-metrics").json()

    state.record_cleanup_event("session.cleanup_begin", "simulated flow", queue=source.metrics())
    server.clear_callbacks()
    state.record_cleanup_event("session.callbacks_cleared", "stream callbacks cleared")
    state.is_running = False
    state.record_cleanup_event("session.cleanup_complete", "simulated flow", queue=source.metrics())
    runtime_payload = live_map_gui._runtime_metrics_payload()

    first = source.next_event("sim-session")
    second = source.next_event("sim-session")

    assert [first.text, second.text] == ["press 1 for billing", "representative"]
    assert any("250 audio frames received" in line for line in state.logs)
    assert stream_payload["last_stream_metrics"]["transcriber_stats"]["backend"] == "simulated"
    assert stream_payload["last_stream_metrics"]["transcriber_stats"]["chunks_seen"] == 50
    assert stream_payload["last_stream_metrics"]["transcriber_stats"]["transcripts_emitted"] == 4
    assert stream_payload["last_stream_metrics"]["last_event"] == "stop"
    assert stream_payload["last_stream_metrics"]["media_bytes_received"] == 250 * 160
    assert stream_payload["last_stream_metrics"]["transcript_filter_stats"] == {
        "received": 4,
        "passed": 2,
        "dropped_short": 1,
        "dropped_dedup": 1,
        "window_size": 2,
        "last_text": "representative",
    }
    assert runtime_payload["session"]["queue"]["puts_total"] == 2
    assert runtime_payload["session"]["queue"]["max_depth_seen"] == 2
    assert runtime_payload["runtime"]["cleanup_count"] == 3
    assert runtime_payload["runtime"]["last_checkpoint"]["stage"] == "session.cleanup_complete"
    assert "replay_visibility" in runtime_payload