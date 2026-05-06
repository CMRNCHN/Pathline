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
from pathlib import Path
from secrets import compare_digest
import threading
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from .transcription import DeepgramTranscriber

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
        self.app = FastAPI()
        self.app.add_api_websocket_route("/stream", self._handle_stream)
        self.app.add_api_websocket_route("/listen", self._handle_listen)
        self.app.add_api_route("/recording-status", self._handle_recording_status, methods=["POST"])

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
        audio_buffer = bytearray()
        BUFFER_FLUSH_SIZE = 160 * 5  # 160 bytes (20ms) * 5 frames = 100ms
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
                    audio_buffer.extend(audio_bytes)

                    # Heartbeat every 5s of audio (250 frames at 20ms each)
                    if media_count - last_status_count >= 250:
                        self._dispatch_status(
                            f"[stream] {media_count} audio frames received "
                            f"({media_count * 20 // 1000}s)"
                        )
                        last_status_count = media_count

                    # Flush buffer to Deepgram in larger chunks to prevent network jitter
                    if connected and len(audio_buffer) >= BUFFER_FLUSH_SIZE:
                        await transcriber.process_audio(bytes(audio_buffer))
                        audio_buffer.clear()

                    # Forward raw audio to any browser /listen clients
                    await self._broadcast_audio(audio_bytes)
                elif message["event"] == "stop":
                    logger.info("Twilio stream stopped")
                    self._dispatch_status(f"[stream] stopped after {media_count} audio frames")
                    if connected and audio_buffer:
                        await transcriber.process_audio(bytes(audio_buffer))
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

        wav_path = recordings_dir / f"{recording_sid}.wav"
        transcript_path = recordings_dir / f"{recording_sid}.txt"

        # Twilio requires auth to download recordings.
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        dl_url = recording_url if recording_url.endswith(".wav") else recording_url + ".wav"

        try:
            self._dispatch_status(f"[recording] downloading {recording_sid}…")
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(dl_url, auth=(account_sid, auth_token))
                resp.raise_for_status()
                wav_path.write_bytes(resp.content)
            logger.info("recording saved: %s (%d bytes)", wav_path, wav_path.stat().st_size)
        except Exception as exc:
            logger.error("recording download failed: %s", exc)
            self._dispatch_status(f"[recording] download failed: {exc}")
            return

        # Transcribe in a thread pool so we don't block the event loop.
        loop = asyncio.get_running_loop()
        try:
            self._dispatch_status(f"[recording] transcribing {recording_sid} with Whisper…")
            transcript = await loop.run_in_executor(None, self._run_whisper, wav_path)
            transcript_path.write_text(transcript, encoding="utf-8")
            logger.info("transcript saved: %s (%d chars)", transcript_path, len(transcript))
            self._dispatch_status(
                f"[recording] ✓ transcript ready ({len(transcript)} chars) → {transcript_path}"
            )
        except ImportError:
            self._dispatch_status(
                "[recording] Whisper not installed — run: pip install openai-whisper && brew install ffmpeg"
            )
        except Exception as exc:
            logger.error("whisper transcription failed: %s", exc, exc_info=True)
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
