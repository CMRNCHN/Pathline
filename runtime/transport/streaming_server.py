"""WebSocket server for Twilio media streaming and transcription.

# spellcheck: ignore=Deepgram,deepgram,DEEPGRAM,mulaw,uvicorn
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import hashlib
from runtime.events.event_bus import bus as EventBus
from runtime.events.event_types import EventType
from runtime.events.event_models import OperationalEvent, EventMetadata
from pathlib import Path
from secrets import compare_digest
import threading
import time
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from runtime.media.audio_pipeline import VoiceActivityDetector, process_audio_frame
from runtime.media.transcript_filter import TranscriptFilter
from runtime.media.transcription import DeepgramTranscriber

logger = logging.getLogger(__name__)

_STREAM_AUTH_ENV = "IVR_STREAM_AUTH_TOKEN"


def _redact_token(token: str | None) -> str:
    if not token:
        return "<empty>"
    if len(token) <= 8:
        return "<redacted>"
    return f"{token[:4]}…{token[-4:]}"


def default_stream_auth_token() -> str:
    """Return a stable stream auth token.

    Uses a deterministic hash of the Twilio credentials so that multiple
    processes (e.g., the GUI server and a separate CLI test runner)
    agree on the token without needing to sync via a file that could
    go stale or cause unauthorized connection rejections.
    """
    env_token = os.environ.get(_STREAM_AUTH_ENV)
    if env_token:
        return env_token

    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if sid and token:
        combined = f"{sid}:{token}".encode("utf-8")
        return hashlib.sha256(combined).hexdigest()[:32]
        
    return "local-dev-insecure-token"


def append_stream_auth_token(url: str | None, token: str) -> str | None:
    """Append a stream auth token to a URL, removing any existing one."""
    if not url:
        return url
    if not token:
        return url

    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)

    # Remove any existing token (stale from previous server restart)
    query = [(k, v) for k, v in query if k not in {"token", "stream_token"}]

    # Append the current token
    query.append(("token", token))
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


class StreamingServer:
    """WebSocket server that receives Twilio media streams and dispatches transcripts."""

    def __init__(self, stream_auth_token: str | None = None) -> None:
        self._callbacks: list[Callable[[str, bool, bool], None]] = []
        self._status_callbacks: list[Callable[[str], None]] = []
        self._listeners: set[WebSocket] = set()
        self._stream_auth_token = (
            default_stream_auth_token() if stream_auth_token is None else stream_auth_token
        )
        # Transcript filter wraps _dispatch_transcript to dedup and drop noise.
        # reset() is called at the start of each stream connection.
        self._transcript_filter = TranscriptFilter(
            on_transcript=self._raw_dispatch_transcript
        )
        self._active_streams = 0
        self._stream_sequence = 0
        self._created_at = time.time()
        self._created_monotonic = time.monotonic()
        self._last_status_message = ""
        self._last_error: str | None = None
        self._current_session_id: str | None = None
        self._stream_idle_timeouts = 0
        self._listen_idle_timeouts = 0
        self._listen_connections_total = 0
        self._last_listen_connected_at: float | None = None
        self._last_listen_disconnected_at: float | None = None
        self._last_stream_connected_at: float | None = None
        self._last_stream_disconnected_at: float | None = None
        self._last_listen_disconnect_reason = ""
        self._last_stream_disconnect_reason = ""
        self._last_listen_close_code: int | None = None
        self._last_stream_close_code: int | None = None
        self._callbacks_cleared_count = 0
        self._last_callbacks_cleared_at: float | None = None
        self._lifecycle_sequence = 0
        self._lifecycle_events: list[dict[str, object]] = []
        self._last_stream_metrics: dict[str, object] = {}
        self._last_recording_artifacts: list[dict[str, object]] = []
        self._event_listeners: set[WebSocket] = set()
        self.app = FastAPI()
        self.app.add_api_websocket_route("/stream", self._handle_stream)
        self.app.add_api_websocket_route("/listen", self._handle_listen)
        self.app.add_api_websocket_route("/ws/events", self._handle_events)
        self.app.add_api_route("/recording-status", self._handle_recording_status, methods=["POST"])
        self.app.add_api_route("/healthz", self._health_check, methods=["GET"])
        self.app.add_api_route("/runtime-metrics", self._runtime_metrics, methods=["GET"])

        # Subscribe to the global EventBus to bridge events to WebSockets
        EventBus.subscribe_all(self._broadcast_event)

    @property
    def stream_auth_token(self) -> str:
        return self._stream_auth_token

    def register_transcript_callback(
        self, callback: Callable[[str, bool, bool], None]
    ) -> None:
        self._callbacks.append(callback)

    def register_status_callback(self, callback: Callable[[str], None]) -> None:
        self._status_callbacks.append(callback)

    def clear_callbacks(self) -> None:
        self._callbacks.clear()
        self._status_callbacks.clear()
        self._callbacks_cleared_count += 1
        self._last_callbacks_cleared_at = time.time()
        self._record_lifecycle_event(
            endpoint="callbacks",
            phase="cleared",
            callbacks_cleared_count=self._callbacks_cleared_count,
        )

    def _dispatch_transcript(self, text: str, is_final: bool, speech_final: bool) -> None:
        """Entry point from transcribers — routes through the dedup filter."""
        if hasattr(self, "session_id") and self.session_id:
            from runtime.supervision.runtime_supervisor import supervisor
            supervisor.update_activity(self.session_id, websocket_connected=True)
        self._transcript_filter(text, is_final, speech_final)

    def _raw_dispatch_transcript(self, text: str, is_final: bool, speech_final: bool) -> None:
        """Deliver a transcript to registered callbacks (post-filter)."""
        if is_final:
            EventBus.publish(OperationalEvent(
                type=EventType.TRANSCRIPT_FINAL,
                payload={"text": text, "speech_final": speech_final},
                meta=EventMetadata(
                    session_id=self._current_session_id,
                    source_component="streaming_server"
                )
            ))
        for cb in self._callbacks:
            try:
                cb(text, is_final, speech_final)
            except Exception as e:
                logger.error("Error in transcript callback: %s", e)

    def _dispatch_status(self, msg: str) -> None:
        self._last_status_message = msg
        if hasattr(self, "session_id") and self.session_id:
            from runtime.supervision.runtime_supervisor import supervisor
            supervisor.update_activity(self.session_id, websocket_connected=True)
        for cb in self._status_callbacks:
            try:
                cb(msg)
            except Exception:
                pass

    def _remember_recording_artifact(self, artifact: dict[str, object]) -> None:
        self._last_recording_artifacts = [
            item for item in self._last_recording_artifacts
            if item.get("recording_sid") != artifact.get("recording_sid")
        ]
        self._last_recording_artifacts.append(dict(artifact))
        self._last_recording_artifacts = self._last_recording_artifacts[-5:]

    def _record_lifecycle_event(self, *, endpoint: str, phase: str, **extra: object) -> None:
        self._lifecycle_sequence += 1
        event: dict[str, object] = {
            "seq": self._lifecycle_sequence,
            "endpoint": endpoint,
            "phase": phase,
            "ts": time.time(),
            "uptime_ms": int((time.monotonic() - self._created_monotonic) * 1000),
        }
        event.update(extra)
        self._lifecycle_events.append(event)
        self._lifecycle_events = self._lifecycle_events[-40:]

    def runtime_metrics(self) -> dict[str, object]:
        uptime_s = round(time.monotonic() - self._created_monotonic, 3)
        return {
            "uptime_s": uptime_s,
            "created_at": self._created_at,
            "active_streams": self._active_streams,
            "listen_clients": len(self._listeners),
            "stream_auth_token_configured": bool(self._stream_auth_token),
            "stream_idle_timeouts": self._stream_idle_timeouts,
            "listen_idle_timeouts": self._listen_idle_timeouts,
            "listen_connections_total": self._listen_connections_total,
            "last_listen_connected_at": self._last_listen_connected_at,
            "last_listen_disconnected_at": self._last_listen_disconnected_at,
            "last_stream_connected_at": self._last_stream_connected_at,
            "last_stream_disconnected_at": self._last_stream_disconnected_at,
            "last_listen_disconnect_reason": self._last_listen_disconnect_reason,
            "last_stream_disconnect_reason": self._last_stream_disconnect_reason,
            "last_listen_close_code": self._last_listen_close_code,
            "last_stream_close_code": self._last_stream_close_code,
            "callbacks_registered": len(self._callbacks),
            "status_callbacks_registered": len(self._status_callbacks),
            "callbacks_cleared_count": self._callbacks_cleared_count,
            "last_callbacks_cleared_at": self._last_callbacks_cleared_at,
            "last_status_message": self._last_status_message,
            "last_error": self._last_error,
            "lifecycle_events": list(self._lifecycle_events),
            "last_stream_metrics": dict(self._last_stream_metrics),
            "recording_artifacts": list(self._last_recording_artifacts),
        }

    def _is_authorized(self, websocket: WebSocket) -> bool:
        if not self._stream_auth_token:
            return True

        supplied = (
            websocket.query_params.get("token")
            or websocket.query_params.get("stream_token")
            or ""
        )
        return bool(supplied) and compare_digest(supplied, self._stream_auth_token)

    async def _reject_unauthorized(self, websocket: WebSocket, endpoint: str) -> None:
        supplied = (
            websocket.query_params.get("token")
            or websocket.query_params.get("stream_token")
        )
        logger.warning(
            "Rejected unauthorized WebSocket connection to %s (expected=%s supplied=%s)",
            endpoint,
            _redact_token(self._stream_auth_token),
            _redact_token(supplied),
        )
        self._record_lifecycle_event(
            endpoint=endpoint,
            phase="rejected_unauthorized",
            supplied=bool(supplied),
        )
        self._dispatch_status(f"[stream] rejected unauthorized connection to {endpoint}")
        await websocket.close(code=1008)

    async def _broadcast_audio(self, audio_bytes: bytes) -> None:
        """Forward raw mulaw audio bytes to every connected /listen client."""
        if not self._listeners:
            return
        dead = set()
        for ws in self._listeners:
            try:
                await ws.send_bytes(audio_bytes)
            except Exception:
                dead.add(ws)
        self._listeners -= dead

    def _broadcast_event(self, event: OperationalEvent) -> None:
        """Broadcast an operational event to all event listeners."""
        if not self._event_listeners:
            return
        msg = json.dumps(event.as_dict())
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                for ws in list(self._event_listeners):
                    try:
                        asyncio.run_coroutine_threadsafe(ws.send_text(msg), loop)
                    except Exception:
                        try:
                            self._event_listeners.remove(ws)
                        except KeyError:
                            pass
        except RuntimeError:
            # No event loop in this thread
            pass

    async def _handle_events(self, websocket: WebSocket) -> None:
        """Handle WebSocket telemetry bridge connections."""
        await websocket.accept()
        self._event_listeners.add(websocket)
        logger.info(f"Telemetry client connected. Total: {len(self._event_listeners)}")
        try:
            while True:
                # Keep connection alive, though we mostly just push
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            if websocket in self._event_listeners:
                self._event_listeners.remove(websocket)
            logger.info(f"Telemetry client disconnected. Total: {len(self._event_listeners)}")

    async def _handle_listen(self, websocket: WebSocket) -> None:
        """Browser clients connect here to receive raw mulaw 8kHz audio for playback."""
        if not self._is_authorized(websocket):
            await self._reject_unauthorized(websocket, "/listen")
            return

        await websocket.accept()
        self._listeners.add(websocket)
        self._listen_connections_total += 1
        self._last_listen_connected_at = time.time()
        self._record_lifecycle_event(
            endpoint="/listen",
            phase="accepted",
            listeners=len(self._listeners),
        )
        logger.info("Listen client connected (%d total)", len(self._listeners))
        listen_idle_timeout_s = float(os.getenv("LISTEN_WS_IDLE_TIMEOUT_S", "30"))
        try:
            # We don't expect inbound messages — just hold the connection open.
            while True:
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=listen_idle_timeout_s)
                except asyncio.TimeoutError:
                    self._listen_idle_timeouts += 1
                    self._record_lifecycle_event(
                        endpoint="/listen",
                        phase="idle_timeout",
                        idle_timeout_s=listen_idle_timeout_s,
                    )
                    logger.debug("Listen websocket idle for %.1fs", listen_idle_timeout_s)
        except WebSocketDisconnect as exc:
            self._last_listen_disconnect_reason = "client_disconnect"
            self._last_listen_close_code = exc.code
            self._record_lifecycle_event(
                endpoint="/listen",
                phase="disconnect",
                close_code=exc.code,
                reason=self._last_listen_disconnect_reason,
            )
        except Exception as exc:
            self._last_listen_disconnect_reason = "error"
            self._record_lifecycle_event(
                endpoint="/listen",
                phase="error",
                error=str(exc),
            )
        finally:
            self._listeners.discard(websocket)
            self._last_listen_disconnected_at = time.time()
            logger.info("Listen client disconnected (%d total)", len(self._listeners))

    async def _handle_stream(self, websocket: WebSocket) -> None:
        if not self._is_authorized(websocket):
            await self._reject_unauthorized(websocket, "/stream")
            return

        await websocket.accept()
        self._active_streams += 1
        self._stream_sequence += 1
        self._last_stream_connected_at = time.time()

        params = dict(websocket.query_params)
        session_id = params.get("session_id") or params.get("CallSid") or f"stream-{self._stream_sequence}"
        self._current_session_id = session_id

        EventBus.publish(OperationalEvent(
            type=EventType.CALL_STARTED,
            payload={"stream_sequence": self._stream_sequence, "session_id": session_id},
            meta=EventMetadata(session_id=session_id, source_component="streaming_server")
        ))
        self._last_stream_disconnect_reason = ""
        self._last_stream_close_code = None
        self._record_lifecycle_event(
            endpoint="/stream",
            phase="accepted",
            active_streams=self._active_streams,
            stream_sequence=self._stream_sequence,
        )
        logger.info("Twilio stream connected (active=%d)", self._active_streams)
        self._dispatch_status("[stream] Twilio connected to /stream")

        # Phase 2: factory selects backend via STT_BACKEND env var.
        # Until stt_service.py exists, fall back to DeepgramTranscriber directly.
        try:
            from runtime.media.stt_service import create_transcriber
            transcriber = create_transcriber(
                on_transcript=self._dispatch_transcript,
                on_status=self._dispatch_status,
            )
        except ImportError:
            from runtime.media.transcription import DeepgramTranscriber
            transcriber = DeepgramTranscriber(
                on_transcript=self._dispatch_transcript,
                on_status=self._dispatch_status,
            )

        stt_backend = os.getenv("STT_BACKEND", "faster-whisper")
        uses_pcm = getattr(transcriber, "INPUT_FORMAT", "mulaw_8k") == "pcm16_16k"
        stream_started_at = time.monotonic()
        self._last_stream_metrics = {
            "stream_sequence": self._stream_sequence,
            "started_at": time.time(),
            "stt_backend": stt_backend,
            "uses_pcm": uses_pcm,
            "media_frames": 0,
            "last_media_at": None,
            "vad_stats": {},
            "transcriber_stats": {},
            "transcript_filter_stats": {},
            "idle_timeouts": 0,
            "stream_status": "connecting",
            "last_event": None,
            "media_bytes_received": 0,
            "audio_buffer_overflows": 0,
            "disconnect_reason": None,
            "close_code": None,
        }

        # Fresh dedup window per call.
        self._transcript_filter.reset(reset_counters=True)

        # VAD is only used when the backend expects processed PCM.
        vad: VoiceActivityDetector | None = None
        vad_init_error: str | None = None
        if uses_pcm:
            async def _queue_vad_utterance(pcm_bytes: bytes) -> None:
                enqueue_started = time.monotonic()
                await transcriber.process_audio(pcm_bytes)
                utterance_ms = int((len(pcm_bytes) / 2) / 16)
                self._last_stream_metrics["last_vad_utterance_ms"] = utterance_ms
                self._last_stream_metrics["last_vad_enqueue_ms"] = round(
                    (time.monotonic() - enqueue_started) * 1000, 1
                )
                self._last_stream_metrics["transcriber_stats"] = (
                    transcriber.stats() if hasattr(transcriber, "stats") else {}
                )

            def _on_vad_utterance(pcm_bytes: bytes) -> None:
                asyncio.create_task(_queue_vad_utterance(pcm_bytes))
            try:
                vad = VoiceActivityDetector(on_utterance=_on_vad_utterance)
            except ImportError as exc:
                vad_init_error = str(exc)
                self._last_error = vad_init_error
                self._dispatch_status(f"[{stt_backend}] ✗ VAD unavailable: {exc}")
                logger.error(
                    "Could not initialize VAD for STT backend (%s): %s",
                    stt_backend,
                    exc,
                )

        if vad_init_error is None:
            connect_started = time.monotonic()
            connected = await transcriber.connect()
            self._last_stream_metrics["stt_connect_ms"] = round(
                (time.monotonic() - connect_started) * 1000, 1
            )
            self._last_stream_metrics["stt_connected"] = connected
            if connected:
                self._last_stream_metrics["stream_status"] = "stt_connected"
                self._dispatch_status(f"[{stt_backend}] ✓ connected — transcripts will flow")
            else:
                self._last_error = f"stt_connect_failed:{stt_backend}"
                self._last_stream_metrics["stream_status"] = "stt_connect_failed"
                self._last_stream_metrics["transcriber_stats"] = (
                    transcriber.stats() if hasattr(transcriber, "stats") else {}
                )
                self._dispatch_status(f"[{stt_backend}] ✗ FAILED to connect")
                logger.error(
                    "Could not connect to STT backend (%s). Transcripts unavailable.",
                    stt_backend,
                )
        else:
            connected = False
            self._last_stream_metrics["stt_connect_ms"] = 0.0
            self._last_stream_metrics["stt_connected"] = False
            self._last_stream_metrics["stream_status"] = "vad_unavailable"

        media_count = 0
        last_status_count = 0
        stream_idle_timeout_s = float(os.getenv("STREAM_WS_IDLE_TIMEOUT_S", "30"))
        # Deepgram path: bounded queue (maxsize=50 ≈ 1s of audio at 20ms/frame)
        # prevents unbounded memory growth if the transcriber falls behind.
        _DEEPGRAM_QUEUE_MAX = 50
        audio_buffer = bytearray()
        BUFFER_FLUSH_SIZE = 160 * 5  # 5 × 20ms = 100ms
        
        # Assign session_id from stream path if possible (e.g. /stream/{session_id})
        self.session_id = websocket.path_params.get("session_id")
        if self.session_id:
            from runtime.supervision.runtime_supervisor import supervisor
            supervisor.update_activity(self.session_id, websocket_connected=True)

        try:
            while True:
                try:
                    data = await asyncio.wait_for(
                        websocket.receive_text(), timeout=stream_idle_timeout_s
                    )
                except asyncio.TimeoutError:
                    self._stream_idle_timeouts += 1
                    self._last_stream_metrics["idle_timeouts"] = (
                        int(self._last_stream_metrics.get("idle_timeouts", 0)) + 1
                    )
                    self._dispatch_status(
                        f"[stream] idle for {int(stream_idle_timeout_s)}s waiting for websocket data"
                    )
                    continue
                message = json.loads(data)
                self._last_stream_metrics["last_event"] = message.get("event")

                if message["event"] == "connected":
                    self._record_lifecycle_event(endpoint="/stream", phase="connected_event")
                    logger.info("Twilio stream started (connected event)")
                elif message["event"] == "start":
                    self._record_lifecycle_event(
                        endpoint="/stream",
                        phase="start_event",
                        stream_sid=message.get("start", {}).get("streamSid"),
                        call_sid=message.get("start", {}).get("callSid"),
                    )
                    logger.info("Twilio stream details: %s", message.get("start"))
                    self._dispatch_status("[stream] Twilio start event received")
                elif message["event"] == "media":
                    audio_bytes = base64.b64decode(message["media"]["payload"])
                    media_count += 1
                    self._last_stream_metrics["media_frames"] = media_count
                    self._last_stream_metrics["last_media_at"] = time.time()
                    self._last_stream_metrics["media_bytes_received"] = (
                        int(self._last_stream_metrics.get("media_bytes_received", 0))
                        + len(audio_bytes)
                    )
                    if media_count == 1:
                        self._record_lifecycle_event(
                            endpoint="/stream",
                            phase="first_media",
                            bytes=len(audio_bytes),
                        )

                    # Heartbeat every 5s (250 frames × 20ms)
                    if media_count - last_status_count >= 250:
                        self._last_stream_metrics["transcriber_stats"] = (
                            transcriber.stats() if hasattr(transcriber, "stats") else {}
                        )
                        if vad is not None:
                            self._last_stream_metrics["vad_stats"] = vad.stats()
                        self._dispatch_status(
                            f"[stream] {media_count} audio frames received "
                            f"({media_count * 20 // 1000}s)"
                        )
                        last_status_count = media_count

                    if connected:
                        if uses_pcm and vad is not None:
                            # PCM path: decode + resample + VAD → utterance → transcriber
                            pcm = process_audio_frame(audio_bytes)
                            vad.feed(pcm)
                        else:
                            # Deepgram path: buffer mulaw, flush in chunks
                            # Drop oldest buffered chunk if we're backing up
                            if len(audio_buffer) >= BUFFER_FLUSH_SIZE * _DEEPGRAM_QUEUE_MAX:
                                audio_buffer = audio_buffer[-BUFFER_FLUSH_SIZE:]
                                self._last_stream_metrics["audio_buffer_overflows"] = (
                                    int(self._last_stream_metrics.get("audio_buffer_overflows", 0))
                                    + 1
                                )
                                logger.warning(
                                    "audio buffer overflow — dropped oldest frames "
                                    "(media_count=%d)", media_count
                                )
                            audio_buffer.extend(audio_bytes)
                            if len(audio_buffer) >= BUFFER_FLUSH_SIZE:
                                await transcriber.process_audio(bytes(audio_buffer))
                                audio_buffer.clear()

                    # Always forward raw mulaw to browser /listen clients
                    await self._broadcast_audio(audio_bytes)

                elif message["event"] == "stop":
                    self._record_lifecycle_event(
                        endpoint="/stream",
                        phase="stop_event",
                        media_frames=media_count,
                    )
                    logger.info("Twilio stream stopped")
                    self._dispatch_status(f"[stream] stopped after {media_count} audio frames")
                    if connected:
                        if uses_pcm and vad is not None:
                            vad.flush()
                        elif audio_buffer:
                            await transcriber.process_audio(bytes(audio_buffer))
                    break
        except WebSocketDisconnect as exc:
            self._last_stream_disconnected_at = time.time()
            self._last_stream_disconnect_reason = "client_disconnect"
            self._last_stream_close_code = exc.code
            logger.info("Twilio stream disconnected")
            self._last_stream_metrics["stream_status"] = "disconnected"
            self._last_stream_metrics["disconnect_reason"] = self._last_stream_disconnect_reason
            self._last_stream_metrics["close_code"] = exc.code
            self._record_lifecycle_event(
                endpoint="/stream",
                phase="disconnect",
                close_code=exc.code,
                reason=self._last_stream_disconnect_reason,
                media_frames=media_count,
            )
            self._dispatch_status(f"[stream] disconnected after {media_count} audio frames")
        except Exception as e:
            self._last_error = str(e)
            self._last_stream_disconnect_reason = "error"
            logger.error("Error handling Twilio stream: %s", e, exc_info=True)
            self._last_stream_metrics["stream_status"] = "error"
            self._last_stream_metrics["disconnect_reason"] = self._last_stream_disconnect_reason
            self._record_lifecycle_event(
                endpoint="/stream",
                phase="error",
                error=str(e),
                media_frames=media_count,
            )
            self._dispatch_status(f"[stream] error: {e}")
        finally:
            self._active_streams = max(0, self._active_streams - 1)
            self._last_stream_disconnected_at = time.time()
            if uses_pcm and vad is not None and connected:
                vad.flush()
            stats = transcriber.stats() if hasattr(transcriber, "stats") else {}
            self._last_stream_metrics["stream_duration_ms"] = round(
                (time.monotonic() - stream_started_at) * 1000, 1
            )
            self._last_stream_metrics["transcriber_stats"] = stats
            self._last_stream_metrics["transcript_filter_stats"] = self._transcript_filter.stats()
            self._last_stream_metrics["vad_stats"] = vad.stats() if vad is not None else {}
            self._last_stream_metrics["disconnect_reason"] = self._last_stream_disconnect_reason
            self._last_stream_metrics["close_code"] = self._last_stream_close_code
            if self._last_stream_metrics.get("stream_status") not in {"error", "disconnected"}:
                self._last_stream_metrics["stream_status"] = "stopped"
            self._record_lifecycle_event(
                endpoint="/stream",
                phase="cleanup_complete",
                stream_status=str(self._last_stream_metrics.get("stream_status")),
                media_frames=media_count,
            )
            if connected:
                if self.session_id:
                    from runtime.supervision.runtime_supervisor import supervisor
                    supervisor.update_activity(self.session_id, websocket_connected=False)

                logger.info("Stream finished: media_count=%d transcriber_stats=%s", media_count, stats)
                self._dispatch_status(
                    f"[stream] final stats: frames={media_count} transcriber={stats}"
                )
                await transcriber.close()
                self._record_lifecycle_event(
                    endpoint="/stream",
                    phase="transcriber_closed",
                    media_frames=media_count,
                )

    async def _health_check(self) -> dict:
        return {
            "status": "ok",
            "stt_backend": os.getenv("STT_BACKEND", "faster-whisper"),
            "tts_backend": os.getenv("TTS_BACKEND", "piper"),
            "active_streams": self._active_streams,
            "listen_clients": len(self._listeners),
            "uptime_s": round(time.monotonic() - self._created_monotonic, 3),
            "last_error": self._last_error,
        }

    async def _runtime_metrics(self) -> dict:
        return self.runtime_metrics()

    async def _handle_recording_status(self, request: Request) -> Response:
        """Receive Twilio recording-completed webhook, download the .wav, and
        transcribe it with Whisper in a background thread."""
        form = await request.form()
        status = form.get("RecordingStatus", "")
        recording_url = str(form.get("RecordingUrl", ""))
        recording_sid = str(form.get("RecordingSid", "unknown"))
        call_sid = str(form.get("CallSid", "unknown"))

        logger.info(
            "recording-status: status=%s call=%s recording=%s url=%s",
            status, call_sid, recording_sid, recording_url,
        )
        self._record_lifecycle_event(
            endpoint="/recording-status",
            phase="received",
            recording_status=status,
            recording_sid=recording_sid,
        )

        if status != "completed" or not recording_url:
            return Response(status_code=204)

        self._dispatch_status(f"[recording] completed for call {call_sid} — queuing transcription")

        # Run download + transcription in a background task so we return 200 fast.
        asyncio.create_task(self._transcribe_recording(recording_url, recording_sid, call_sid))
        return Response(status_code=200)

    async def _transcribe_recording(
        self, recording_url: str, recording_sid: str, call_sid: str
    ) -> None:
        reports_dir = Path(os.environ.get("IVR_REPORTS_DIR", "~/.ivr_assessor/reports")).expanduser()
        recordings_dir = reports_dir / "recordings"
        recordings_dir.mkdir(parents=True, exist_ok=True)

        # Twilio requires auth to download recordings.
        # Ensure recording URL ends with .wav
        dl_url = recording_url if recording_url.endswith(".wav") else recording_url + ".wav"

        wav_path = recordings_dir / f"{recording_sid}.wav"
        transcript_path = recordings_dir / f"{recording_sid}.txt"
        artifact = {
            "call_sid": call_sid,
            "recording_sid": recording_sid,
            "recording_url": dl_url,
            "wav_path": str(wav_path),
            "transcript_path": str(transcript_path),
            "status": "queued",
            "updated_at": time.time(),
        }
        self._remember_recording_artifact(artifact)

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")

        try:
            self._dispatch_status(f"[recording] downloading {recording_sid}…")
            self._record_lifecycle_event(
                endpoint="/recording-status",
                phase="download_started",
                recording_sid=recording_sid,
            )
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(dl_url, auth=(account_sid, auth_token))
                resp.raise_for_status()
                wav_path.write_bytes(resp.content)
            artifact.update({
                "recording_url": dl_url,
                "status": "downloaded",
                "wav_bytes": wav_path.stat().st_size,
                "updated_at": time.time(),
            })
            self._remember_recording_artifact(artifact)
            logger.info("recording saved: %s (%d bytes)", wav_path, wav_path.stat().st_size)
            self._record_lifecycle_event(
                endpoint="/recording-status",
                phase="downloaded",
                recording_sid=recording_sid,
                wav_bytes=wav_path.stat().st_size,
            )
        except Exception as exc:
            logger.error("recording download failed: %s", exc)
            artifact.update({"status": "download_failed", "error": str(exc), "updated_at": time.time()})
            self._remember_recording_artifact(artifact)
            self._record_lifecycle_event(
                endpoint="/recording-status",
                phase="download_failed",
                recording_sid=recording_sid,
                error=str(exc),
            )
            self._dispatch_status(f"[recording] download failed: {exc}")
            return

        # Transcribe in a thread pool so we don't block the event loop.
        loop = asyncio.get_running_loop()
        try:
            self._dispatch_status(f"[recording] transcribing {recording_sid} with Whisper…")
            transcript = await loop.run_in_executor(None, self._run_whisper, wav_path)
            transcript_path.write_text(transcript, encoding="utf-8")
            artifact.update({
                "status": "transcribed",
                "transcript_chars": len(transcript),
                "updated_at": time.time(),
            })
            self._remember_recording_artifact(artifact)
            logger.info("transcript saved: %s (%d chars)", transcript_path, len(transcript))
            self._record_lifecycle_event(
                endpoint="/recording-status",
                phase="transcribed",
                recording_sid=recording_sid,
                transcript_chars=len(transcript),
            )
            self._dispatch_status(
                f"[recording] ✓ transcript ready ({len(transcript)} chars) → {transcript_path}"
            )
        except ImportError:
            artifact.update({
                "status": "transcriber_missing",
                "error": "Whisper not installed",
                "updated_at": time.time(),
            })
            self._remember_recording_artifact(artifact)
            self._record_lifecycle_event(
                endpoint="/recording-status",
                phase="transcriber_missing",
                recording_sid=recording_sid,
            )
            self._dispatch_status(
                "[recording] Whisper not installed — run: pip install openai-whisper && brew install ffmpeg"
            )
        except Exception as exc:
            logger.error("whisper transcription failed: %s", exc, exc_info=True)
            artifact.update({"status": "transcription_failed", "error": str(exc), "updated_at": time.time()})
            self._remember_recording_artifact(artifact)
            self._record_lifecycle_event(
                endpoint="/recording-status",
                phase="transcription_failed",
                recording_sid=recording_sid,
                error=str(exc),
            )
            self._dispatch_status(f"[recording] transcription failed: {exc}")

    @staticmethod
    def _run_whisper(wav_path: Path) -> str:
        from .audio_quality import LocalWhisperTranscriber
        model_size = os.environ.get("WHISPER_MODEL", "base")
        t = LocalWhisperTranscriber(model_size=model_size)
        return t.transcribe(wav_path)

    def start_in_background(self, host: str = "127.0.0.1", port: int = 8000) -> threading.Thread:
        import uvicorn

        def run() -> None:
            uvicorn.run(self.app, host=host, port=port, log_level="warning")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread


# Module-level default instance for simple single-process usage.
_default_server = StreamingServer()
app = _default_server.app
register_transcript_callback = _default_server.register_transcript_callback


def start_server_in_background(host: str = "127.0.0.1", port: int = 8000) -> threading.Thread:
    return _default_server.start_in_background(host=host, port=port)