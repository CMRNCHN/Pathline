from __future__ import annotations

import base64
import json
import logging
import os
from secrets import compare_digest, token_urlsafe
import threading
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from .transcription import DeepgramTranscriber

logger = logging.getLogger(__name__)

_STREAM_AUTH_ENV = "IVR_STREAM_AUTH_TOKEN"
_GENERATED_STREAM_AUTH_TOKEN = token_urlsafe(32)


def default_stream_auth_token() -> str:
    """Return the process-wide stream token.

    **For production/stable setups:**
    Set IVR_STREAM_AUTH_TOKEN environment variable to a fixed value. This ensures
    the token remains consistent across server restarts, preventing Twilio
    "unauthorized connection" errors when it reconnects after the server restarts.

    **For development/testing:**
    If not set, a random per-process token is generated on startup and automatically
    injected into GUI URLs. If the server restarts, the token changes and the GUI
    will auto-refresh the stream URL on the next session start.

    Example:
        export IVR_STREAM_AUTH_TOKEN="your-stable-token-here"
        ./run_ivr_assessor.sh live-map-gui
    """
    return os.environ.get(_STREAM_AUTH_ENV) or _GENERATED_STREAM_AUTH_TOKEN


def append_stream_auth_token(url: str | None, token: str | None = None) -> str | None:
    if not url:
        return url

    token = default_stream_auth_token() if token is None else token
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
        self.app = FastAPI()
        self.app.add_api_websocket_route("/stream", self._handle_stream)
        self.app.add_api_websocket_route("/listen", self._handle_listen)

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

    def _dispatch_transcript(self, text: str, is_final: bool, speech_final: bool) -> None:
        for cb in self._callbacks:
            try:
                cb(text, is_final, speech_final)
            except Exception as e:
                logger.error("Error in transcript callback: %s", e)

    def _dispatch_status(self, msg: str) -> None:
        for cb in self._status_callbacks:
            try:
                cb(msg)
            except Exception:
                pass

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
        logger.warning("Rejected unauthorized WebSocket connection to %s", endpoint)
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

    async def _handle_listen(self, websocket: WebSocket) -> None:
        """Browser clients connect here to receive raw mulaw 8kHz audio for playback."""
        if not self._is_authorized(websocket):
            await self._reject_unauthorized(websocket, "/listen")
            return

        await websocket.accept()
        self._listeners.add(websocket)
        logger.info("Listen client connected (%d total)", len(self._listeners))
        try:
            # We don't expect inbound messages — just hold the connection open.
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            self._listeners.discard(websocket)
            logger.info("Listen client disconnected (%d total)", len(self._listeners))

    async def _handle_stream(self, websocket: WebSocket) -> None:
        if not self._is_authorized(websocket):
            await self._reject_unauthorized(websocket, "/stream")
            return

        await websocket.accept()
        logger.info("Twilio stream connected")
        self._dispatch_status("[stream] Twilio connected to /stream")

        transcriber = DeepgramTranscriber(
            on_transcript=self._dispatch_transcript,
            on_status=self._dispatch_status,
        )
        connected = await transcriber.connect()
        if connected:
            self._dispatch_status("[deepgram] ✓ connected — transcripts will flow")
        else:
            self._dispatch_status("[deepgram] ✗ FAILED to connect — check DEEPGRAM_API_KEY")
            logger.error("Could not connect to Deepgram. Transcripts will not be available.")

        media_count = 0
        last_status_count = 0
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)

                if message["event"] == "connected":
                    logger.info("Twilio stream started (connected event)")
                elif message["event"] == "start":
                    logger.info("Twilio stream details: %s", message["start"])
                    self._dispatch_status("[stream] Twilio start event received")
                elif message["event"] == "media":
                    payload = message["media"]["payload"]
                    audio_bytes = base64.b64decode(payload)
                    media_count += 1
                    # Heartbeat every 5s of audio (250 frames at 20ms each)
                    if media_count - last_status_count >= 250:
                        self._dispatch_status(
                            f"[stream] {media_count} audio frames received "
                            f"({media_count * 20 // 1000}s)"
                        )
                        last_status_count = media_count
                    if connected:
                        await transcriber.process_audio(audio_bytes)
                    # Forward raw audio to any browser /listen clients
                    await self._broadcast_audio(audio_bytes)
                elif message["event"] == "stop":
                    logger.info("Twilio stream stopped")
                    self._dispatch_status(f"[stream] stopped after {media_count} audio frames")
                    break
        except WebSocketDisconnect:
            logger.info("Twilio stream disconnected")
            self._dispatch_status(f"[stream] disconnected after {media_count} audio frames")
        except Exception as e:
            logger.error("Error handling Twilio stream: %s", e, exc_info=True)
            self._dispatch_status(f"[stream] error: {e}")
        finally:
            if connected:
                stats = transcriber.stats() if hasattr(transcriber, "stats") else {}
                logger.info("Stream finished: media_count=%d transcriber_stats=%s", media_count, stats)
                self._dispatch_status(
                    f"[stream] final stats: frames={media_count} transcriber={stats}"
                )
                await transcriber.close()

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
