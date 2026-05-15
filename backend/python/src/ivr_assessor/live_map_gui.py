from __future__ import annotations

import json
import logging
import os
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import map_store
from .inspection import build_runtime_diagnostics, build_session_snapshot
from .live_map import LiveMappingSession
from .models import CallEvent
from .response_library import ResponseLibrary
from .startup_runtime import bootstrap_runtime
from .streaming_server import (
    StreamingServer,
    append_stream_auth_token,
    default_stream_auth_token,
)
from .twilio_client import TwilioTelephonyClient
from .backend.ui.ui_state import (
    RECORDINGS_DIR,
    REPLAYS_DIR,
    REPORTS_DIR,
    SNAPSHOTS_DIR,
    STATE,
    RS_STATE,
    AppState,
    QueuePromptSource,
)
from .events.event_sink import sink as EventSink
from .backend.ui.template_loader import render_index, TEMPLATE_INDEX
from .backend.ui.frontend_assets import load_static
from .backend.routes import (
    mapper_routes,
    run_suite_routes,
    replay_routes,
    telecom_test_routes,
    telemetry_routes,
)
from .backend.routes.run_suite_routes import normalize_suite_filename as _normalize_suite_filename  # noqa: F401 (public re-export for tests)

_STREAM_PORT = 8081
_GUI_PORT = 8080
logger = logging.getLogger(__name__)

# Persistent streaming server — started once at GUI launch so it's always ready.
_persistent_stream: StreamingServer | None = None
_default_stream_url: str | None = None


# ── Infrastructure helpers ────────────────────────────────────────────────────

def _wait_for_port(host: str, port: int, timeout: float = 8.0) -> bool:
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _free_port(port: int) -> None:
    import subprocess, os as _os, signal
    try:
        out = subprocess.check_output(["lsof", "-t", f"-i:{port}"], stderr=subprocess.DEVNULL)
        for pid in out.decode().splitlines():
            if pid.strip():
                try:
                    _os.kill(int(pid.strip()), signal.SIGKILL)
                except Exception:
                    pass
    except Exception:
        pass
    try:
        subprocess.call(["fuser", "-k", "-9", f"{port}/tcp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    time.sleep(0.5)


def _ensure_stream_server() -> StreamingServer | None:
    global _persistent_stream
    if _persistent_stream is None:
        STATE.record_startup_event("stream_server.prepare", f"freeing port {_STREAM_PORT}")
        STATE.record_runtime_checkpoint(
            "stream_server.prepare",
            f"freeing port {_STREAM_PORT}",
            category="startup",
            port=_STREAM_PORT,
        )
        _free_port(_STREAM_PORT)
        try:
            srv = StreamingServer()
            STATE.record_startup_event("stream_server.start", f"binding port {_STREAM_PORT}")
            STATE.record_runtime_checkpoint(
                "stream_server.start",
                f"binding port {_STREAM_PORT}",
                category="startup",
                port=_STREAM_PORT,
            )
            srv.start_in_background(host="0.0.0.0", port=_STREAM_PORT)
            if not _wait_for_port("127.0.0.1", _STREAM_PORT, timeout=8.0):
                STATE.logs.append(f"Warning: stream server did not bind to :{_STREAM_PORT} within 8s")
                STATE.record_startup_event("stream_server.timeout", f"bind timeout on {_STREAM_PORT}")
                STATE.record_runtime_checkpoint(
                    "stream_server.timeout",
                    f"bind timeout on {_STREAM_PORT}",
                    category="startup",
                    port=_STREAM_PORT,
                )
            _persistent_stream = srv
            STATE.record_startup_event("stream_server.ready", f"listening on {_STREAM_PORT}")
            STATE.record_runtime_checkpoint(
                "stream_server.ready",
                f"listening on {_STREAM_PORT}",
                category="startup",
                port=_STREAM_PORT,
            )
        except Exception as exc:
            STATE.logs.append(f"Stream server start failed: {exc}")
            STATE.record_startup_event("stream_server.error", str(exc))
            STATE.record_runtime_checkpoint(
                "stream_server.error",
                str(exc),
                category="startup",
                port=_STREAM_PORT,
            )
            return None
    return _persistent_stream


def _detect_ngrok_url() -> str | None:
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=1.5) as r:
            data = json.loads(r.read())
        for tun in data.get("tunnels", []):
            if tun.get("proto") == "https":
                addr = tun.get("config", {}).get("addr", "")
                if str(_STREAM_PORT) in addr:
                    return tun["public_url"]
        for tun in data.get("tunnels", []):
            if tun.get("proto") == "https":
                return tun["public_url"]
    except Exception:
        return None
    return None


def _to_wss(url: str | None, force_token: str | None = None) -> str | None:
    if not url:
        return None
    wss = url.strip().replace("https://", "wss://", 1).replace("http://", "ws://", 1)
    parts = urlsplit(wss)
    path = parts.path.rstrip("/")
    if not path.endswith("/stream"):
        path = f"{path}/stream" if path else "/stream"
    token = force_token if force_token else (
        _persistent_stream.stream_auth_token if _persistent_stream else default_stream_auth_token()
    )
    return append_stream_auth_token(
        urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment)),
        token=token,
    )


def _diagnose() -> dict:
    issues: list[str] = []
    fixes: list[dict] = []
    twilio: dict = {"ok": False, "account": None, "error": None}
    sid   = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not sid or not token:
        twilio["error"] = "Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN in environment"
        issues.append("Twilio credentials missing — set them in ⚙ Settings")
    else:
        try:
            from twilio.rest import Client
            client = Client(sid, token)
            account = client.api.accounts(sid).fetch()
            twilio = {"ok": True, "account": account.friendly_name, "error": None}
        except Exception as exc:
            twilio["error"] = str(exc)
            issues.append(f"Twilio auth failed: {exc}")
    deepgram_key = os.environ.get("DEEPGRAM_API_KEY", "")
    deepgram = {"ok": bool(deepgram_key), "error": None if deepgram_key else "Missing DEEPGRAM_API_KEY"}
    if not deepgram_key:
        issues.append("Deepgram API key missing — transcription will not work (set DEEPGRAM_API_KEY in .env)")
    import socket
    stream_listening = False
    try:
        with socket.create_connection(("127.0.0.1", _STREAM_PORT), timeout=0.5):
            stream_listening = True
    except OSError:
        pass
    if not stream_listening:
        issues.append(f"Stream server not listening on :{_STREAM_PORT}")
        fixes.append({"action": "restart_stream_server", "label": "Restart stream server"})
    ngrok_url = _detect_ngrok_url()
    configured_backend = os.environ.get("TUNNEL_BACKEND", "ngrok").lower()
    cloudflare_configured = bool(_default_stream_url and "trycloudflare.com" in _default_stream_url)
    ngrok = {"running": ngrok_url is not None, "url": ngrok_url, "expected_port": _STREAM_PORT}
    tunnel = {
        "backend": "cloudflare" if cloudflare_configured else configured_backend,
        "configured_url": _default_stream_url,
        "ngrok_detected": ngrok_url is not None,
    }
    if configured_backend == "cloudflare" or cloudflare_configured:
        if not _default_stream_url:
            issues.append("Cloudflare tunnel backend selected but no public stream URL is wired into the GUI")
    elif not ngrok_url:
        issues.append(f"ngrok is not running — run: ngrok http {_STREAM_PORT}")
        fixes.append({"action": "start_ngrok", "label": f"Start ngrok on :{_STREAM_PORT}"})
    suggested_wss = _to_wss(_default_stream_url or ngrok_url) if (_default_stream_url or ngrok_url) else None
    return {
        "twilio": twilio,
        "deepgram": deepgram,
        "stream_server": {"listening": stream_listening, "port": _STREAM_PORT},
        "ngrok": ngrok,
        "tunnel": tunnel,
        "suggested_stream_url": suggested_wss,
        "issues": issues,
        "fixes": fixes,
        "ok": not issues,
    }


def _artifact_directory_summary(directory: Path) -> dict[str, Any]:
    expanded = directory.expanduser()
    if not expanded.exists():
        return {
            "path": str(expanded),
            "exists": False,
            "file_count": 0,
            "latest": None,
        }

    files = [entry for entry in expanded.iterdir() if entry.is_file()]
    latest = max(files, key=lambda entry: entry.stat().st_mtime, default=None)
    latest_payload = None
    if latest is not None:
        stat = latest.stat()
        latest_payload = {
            "name": latest.name,
            "path": str(latest),
            "size_bytes": stat.st_size,
            "updated_at": stat.st_mtime,
        }
    return {
        "path": str(expanded),
        "exists": True,
        "file_count": len(files),
        "latest": latest_payload,
    }


def _staleness_payload(stream_metrics: dict[str, Any]) -> dict[str, Any]:
    candidate_timestamps: list[float] = []
    startup_events = STATE.startup_events
    runtime_snapshot = STATE.runtime_checkpoint_snapshot()
    last_checkpoint = runtime_snapshot.get("last_checkpoint")

    if startup_events:
        candidate_timestamps.append(float(startup_events[-1]["ts"]))
    if isinstance(last_checkpoint, dict) and last_checkpoint.get("ts") is not None:
        candidate_timestamps.append(float(last_checkpoint["ts"]))

    for key in (
        "last_listen_connected_at",
        "last_listen_disconnected_at",
        "last_stream_connected_at",
        "last_stream_disconnected_at",
    ):
        value = stream_metrics.get(key)
        if isinstance(value, (int, float)):
            candidate_timestamps.append(float(value))

    for artifact in stream_metrics.get("recording_artifacts", []):
        updated_at = artifact.get("updated_at")
        if isinstance(updated_at, (int, float)):
            candidate_timestamps.append(float(updated_at))

    last_activity_at = max(candidate_timestamps) if candidate_timestamps else None
    stale_after_s = float(os.getenv("RUNTIME_STALE_AFTER_S", "300"))
    idle_for_s = round(time.time() - last_activity_at, 3) if last_activity_at is not None else None
    is_stale = bool(
        idle_for_s is not None
        and idle_for_s >= stale_after_s
        and not STATE.is_running
        and not stream_metrics.get("active_streams")
        and not stream_metrics.get("listen_clients")
    )
    return {
        "last_activity_at": last_activity_at,
        "idle_for_s": idle_for_s,
        "stale_after_s": stale_after_s,
        "is_stale": is_stale,
    }


def _runtime_metrics_payload() -> dict[str, Any]:
    stream_metrics = (
        _persistent_stream.runtime_metrics() if _persistent_stream is not None else {}
    )
    session_elapsed_ms = (
        int((time.time() - STATE.start_time) * 1000)
        if STATE.start_time is not None
        else None
    )
    reports_dir = Path(os.environ.get("IVR_REPORTS_DIR", str(REPORTS_DIR))).expanduser()
    recordings_dir = Path(os.environ.get("IVR_RECORDINGS_DIR", str(RECORDINGS_DIR))).expanduser()
    session_queue_metrics = STATE.source.metrics() if STATE.source is not None else None
    return {
        "startup": STATE.startup_snapshot(),
        "runtime": STATE.runtime_checkpoint_snapshot(),
        "session": {
            "is_running": STATE.is_running,
            "target": STATE.target,
            "elapsed_ms": session_elapsed_ms,
            "ledger_events": len(STATE.session.ledger.all()) if STATE.session else 0,
            "queue": session_queue_metrics,
            "error": STATE.error,
        },
        "stream_server": stream_metrics,
        "last_session": STATE.last_session_snapshot,
        "replay_visibility": {
            "reports_dir": str(reports_dir),
            "recordings_dir": str(recordings_dir),
            "replays_dir": str(REPLAYS_DIR),
            "snapshots_dir": str(SNAPSHOTS_DIR),
            "recording_status_callback_configured": bool(
                os.environ.get("TWILIO_RECORDING_STATUS_CALLBACK")
            ),
            "recording_artifacts": stream_metrics.get("recording_artifacts", []),
            "reports": _artifact_directory_summary(reports_dir),
            "recordings": _artifact_directory_summary(recordings_dir),
            "replays": _artifact_directory_summary(REPLAYS_DIR),
            "snapshots": _artifact_directory_summary(SNAPSHOTS_DIR),
        },
        "staleness": _staleness_payload(stream_metrics),
    }


def _active_session_snapshot() -> dict[str, Any] | None:
    if STATE.session is None:
        return None
    return build_session_snapshot(
        target=STATE.target,
        started_at=STATE.start_time,
        ended_at=time.time(),
        manual_mode=bool(STATE.session.manual_mode),
        events=STATE.session.ledger.all(),
        graph=STATE.session.mapper.graph(),
        queue_metrics=STATE.source.metrics() if STATE.source is not None else None,
        error=STATE.error,
    )


def _runtime_diagnostics_payload() -> dict[str, Any]:
    runtime_metrics = _runtime_metrics_payload()
    return build_runtime_diagnostics(
        runtime_metrics,
        active_session_snapshot=_active_session_snapshot(),
    )


def _start_ngrok_subprocess() -> dict:
    import shutil, subprocess
    binary = shutil.which("ngrok") or "/opt/homebrew/bin/ngrok"
    if not binary or not os.path.exists(binary):
        return {"ok": False, "error": "ngrok binary not found in PATH"}
    try:
        subprocess.Popen(
            [binary, "http", str(_STREAM_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    for _ in range(40):
        time.sleep(0.25)
        url = _detect_ngrok_url()
        if url:
            return {"ok": True, "url": url}
    return {"ok": False, "error": "ngrok did not respond within 10s"}


def _poll_call_status(client: Any, call_sid: str) -> None:
    last_status = None
    poll_count = 0
    while poll_count < 240:
        try:
            call = client.calls(call_sid).fetch()
            status = call.status
            if status != last_status:
                STATE.logs.append(f"[twilio] call {call_sid[:10]}… status: {status}")
                last_status = status
                if status in ("completed", "busy", "failed", "no-answer", "canceled"):
                    if call.duration:
                        STATE.logs.append(f"[twilio] duration: {call.duration}s")
                    return
        except Exception:
            pass
        time.sleep(0.5)
        poll_count += 1


# ── Session coordinator ───────────────────────────────────────────────────────

def _run_session_thread(
    target: str,
    user: str,
    sid: str,
    token: str,
    tnum: str,
    stream_url: str | None,
    manual_mode: bool = False,
) -> None:
    import threading
    STATE.logs.append(f"[debug] Starting session thread for target: {target}")
    STATE.record_runtime_checkpoint(
        "session.thread_start",
        f"target={target}",
        category="session",
        manual_mode=manual_mode,
    )
    stream_url = stream_url or _default_stream_url
    STATE.logs.append(f"[debug] Input stream_url: {stream_url}")
    try:
        source = QueuePromptSource()
        STATE.source = source
        STATE.target = target
        STATE.start_time = time.time()

        active_token = None
        live_ngrok = _detect_ngrok_url()
        if stream_url or live_ngrok:
            srv = _ensure_stream_server()
            STATE.streaming_server = srv
            active_token = srv.stream_auth_token if srv else default_stream_auth_token()

        if live_ngrok:
            corrected = _to_wss(live_ngrok, force_token=active_token)
            if stream_url and stream_url != corrected:
                STATE.logs.append(f"[fix] stream URL was '{stream_url}'")
                STATE.logs.append(f"[fix] using live ngrok URL '{corrected}' instead")
            stream_url = corrected
        elif stream_url:
            stream_url = _to_wss(stream_url, force_token=active_token)
            STATE.logs.append("[warn] ngrok not detected on :4040 — using saved stream URL")
        else:
            STATE.logs.append("[warn] no stream URL and no ngrok detected — transcription will be disabled")

        STATE.logs.append(f"[debug] Final computed stream_url for Twilio: {stream_url}")
        STATE.record_runtime_checkpoint(
            "session.stream_url_resolved",
            stream_url or "<disabled>",
            category="session",
            stream_enabled=bool(stream_url),
        )

        if stream_url:
            srv = STATE.streaming_server
            _on_transcript, _on_status = _build_stream_callbacks(source=source, state=STATE)

            if srv:
                srv.clear_callbacks()
                srv.register_transcript_callback(_on_transcript)
                srv.register_status_callback(_on_status)
                STATE.record_runtime_checkpoint(
                    "session.stream_callbacks_registered",
                    f"callbacks ready on {_STREAM_PORT}",
                    category="session",
                    stream_port=_STREAM_PORT,
                )
                STATE.logs.append(f"[ok] stream server ready on :{_STREAM_PORT}")
                STATE.logs.append(f"[ok] Twilio will stream to {stream_url}")
                if not os.environ.get("DEEPGRAM_API_KEY"):
                    STATE.logs.append("[warn] DEEPGRAM_API_KEY not set — transcripts will be disabled")
            else:
                STATE.logs.append("[error] stream server unavailable — transcription disabled")

        existing = map_store.load_map(target)
        prior_graph = existing.get("graph", {}) if existing else {}
        if prior_graph:
            STATE.logs.append(f"Loaded saved map with {len(prior_graph)} prior nodes")
            STATE.graph = prior_graph
        STATE.record_runtime_checkpoint(
            "session.map_loaded",
            f"prior_nodes={len(prior_graph)}",
            category="session",
            prior_nodes=len(prior_graph),
        )

        telephony = TwilioTelephonyClient(
            account_sid=sid or None,
            auth_token=token or None,
            twilio_number=tnum or None,
            user_phone_number=user or None,
            stream_url=stream_url,
        )
        STATE.logs.append(f"[dial] calling {target}…")
        call_sid = telephony.dial(target)
        STATE.logs.append(f"[twilio] call SID: {call_sid}")

        session = LiveMappingSession(
            target_number=target,
            response_mode="dtmf",
            prompt_source=source,
            telephony=telephony,
            response_library=ResponseLibrary(clips=[]),
            manual_mode=manual_mode,
            session_id=call_sid,
        )
        STATE.session = session

        from .runtime.runtime_supervisor import supervisor
        STATE.is_running = True
        try:
            summary = supervisor.supervised_session(call_sid, session.run, call_sid=call_sid)
            STATE.graph = summary.graph
            STATE.record_runtime_checkpoint(
                "session.run_complete",
                "session ended cleanly",
                category="session",
                graph_nodes=len(summary.graph),
                queue=source.metrics(),
            )
            STATE.logs.append("[ok] session ended cleanly")
        finally:
            STATE.is_running = False
        try:
            map_store.save_map(target, summary.graph)
            STATE.logs.append(f"Saved map for {target}")
            STATE.record_runtime_checkpoint(
                "session.map_saved",
                f"target={target}",
                category="session",
                graph_nodes=len(summary.graph),
            )
        except Exception as exc:
            STATE.logs.append(f"Save error: {exc}")
            STATE.record_runtime_checkpoint(
                "session.map_save_error",
                str(exc),
                category="session",
            )

    except Exception as e:
        msg = str(e)
        STATE.error = msg
        STATE.logs.append(f"Error: {msg}")
        STATE.record_runtime_checkpoint("session.error", msg, category="session")
    finally:
        if STATE.session is not None:
            STATE.last_session_snapshot = build_session_snapshot(
                target=target,
                started_at=STATE.start_time,
                ended_at=time.time(),
                manual_mode=bool(STATE.session.manual_mode),
                events=STATE.session.ledger.all(),
                graph=STATE.session.mapper.graph(),
                queue_metrics=STATE.source.metrics() if STATE.source is not None else None,
                error=STATE.error,
            )
        STATE.record_cleanup_event(
            "session.cleanup_begin",
            f"target={target}",
            queue=STATE.source.metrics() if STATE.source is not None else None,
        )
        STATE.is_running = False
        STATE.session = None
        if _persistent_stream is not None:
            try:
                _persistent_stream.clear_callbacks()
                STATE.record_cleanup_event(
                    "session.callbacks_cleared",
                    "stream callbacks cleared",
                )
            except Exception:
                STATE.record_cleanup_event(
                    "session.callbacks_clear_failed",
                    "stream callback cleanup failed",
                )
        STATE.record_cleanup_event(
            "session.cleanup_complete",
            f"target={target}",
            queue=STATE.source.metrics() if STATE.source is not None else None,
        )


def _build_stream_callbacks(
    *,
    source: QueuePromptSource,
    state: AppState,
) -> tuple[Callable[[str, bool, bool], None], Callable[[str], None]]:
    utterance: dict[str, list[str]] = {"chunks": []}

    def _flush_utterance() -> None:
        joined = " ".join(utterance["chunks"]).strip()
        utterance["chunks"] = []
        if joined:
            state.logs.append(f"[transcript] {joined}")
            source.prompt_queue.put(joined)
        state.live_caption = ""

    def _on_transcript(text: str, is_final: bool, speech_final: bool) -> None:
        stripped = text.strip()
        if not stripped:
            if speech_final:
                _flush_utterance()
            return
        if is_final:
            utterance["chunks"].append(stripped)
            state.live_caption = " ".join(utterance["chunks"])
            if speech_final:
                _flush_utterance()
            return
        pending = " ".join(utterance["chunks"])
        state.live_caption = (pending + " " + stripped).strip() if pending else stripped

    def _on_status(msg: str) -> None:
        state.logs.append(msg)

    return _on_transcript, _on_status


# ── HTTP request handler (thin dispatcher) ────────────────────────────────────

class LiveMapRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self) -> None:
        if self.path == "/":
            body = render_index(_default_stream_url, _to_wss)
            self._raw(200, "text/html; charset=utf-8", body)
            return
        if self.path.startswith("/static/"):
            status, ctype, body = load_static(self.path[len("/static/"):])
            if status == 200:
                self._raw(200, ctype, body)
            else:
                self.send_response(status); self.end_headers()
            return
        if self.path == "/api/status":
            self._json(mapper_routes.build_status_payload()); return
        if self.path == "/api/config":
            self._json(mapper_routes.get_config(
                _default_stream_url, _persistent_stream, _to_wss, default_stream_auth_token
            )); return
        if self.path == "/api/maps":
            self._json(mapper_routes.get_maps()); return
        if self.path == "/api/diagnose":
            self._json(_diagnose()); return
        if self.path == "/api/runtime-metrics":
            self._json(_runtime_metrics_payload()); return
        if self.path == "/api/runtime-diagnostics":
            self._json(_runtime_diagnostics_payload()); return
        if self.path == "/api/suites":
            self._json(run_suite_routes.list_suites()); return
        if self.path.startswith("/api/maps/"):
            from urllib.parse import unquote
            self._json(mapper_routes.get_map(unquote(self.path[len("/api/maps/"):]))); return
        if self.path == "/api/run-suites":
            self._json(run_suite_routes.list_run_suites()); return
        if self.path == "/api/replays":
            self._json(replay_routes.get_replays()); return
        if self.path.startswith("/api/replays/"):
            from urllib.parse import unquote, urlparse, parse_qs
            parsed = urlparse(self.path)
            parts = parsed.path[len("/api/replays/"):].split("/")
            session_id = unquote(parts[0])
            
            if len(parts) > 1:
                sub_route = parts[1]
                if sub_route == "events":
                    self._json(replay_routes.get_replay_events(session_id)); return
                if sub_route == "timeline":
                    self._json(replay_routes.get_replay_timeline(session_id)); return
                if sub_route == "state":
                    offset = int(parts[2]) if len(parts) > 2 else None
                    self._json(replay_routes.get_replay(session_id, offset=offset)); return
                if sub_route == "diff":
                    from_off = int(parts[2]) if len(parts) > 2 else 0
                    to_off = int(parts[3]) if len(parts) > 3 else 0
                    self._json(replay_routes.get_replay_diff(session_id, from_off, to_off)); return
            
            # Default: full reconstruction
            params = parse_qs(parsed.query)
            offset = int(params.get("offset", [0])[0]) if "offset" in params else None
            self._json(replay_routes.get_replay(session_id, offset=offset)); return
        if self.path.startswith("/api/run-suites/") and self.path.endswith("/poll"):
            from urllib.parse import unquote
            suite_id = unquote(self.path[len("/api/run-suites/"):-len("/poll")])
            self._json(run_suite_routes.poll_run_suite(suite_id)); return
        if self.path.startswith("/api/run-suites/") and "/export" in self.path:
            from urllib.parse import unquote
            from .run_suites.loader import load_suite, export_suite_json
            suite_id = unquote(self.path.split("/")[3])
            try:
                suite = load_suite(suite_id, suites_dir=run_suite_routes.RUN_SUITES_DIR)
                body = export_suite_json(suite).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Disposition", f'attachment; filename="{suite_id}.json"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_response(404); self.end_headers()
            return
        if self.path == "/api/telecom-tests":
            self._json(telecom_test_routes.get_telecom_tests()); return
        if self.path.startswith("/api/telecom-tests/"):
            from urllib.parse import unquote
            parts = self.path[len("/api/telecom-tests/"):].split("/")
            test_id = unquote(parts[0])
            if len(parts) > 1 and parts[1] == "evidence":
                 self._json(telecom_test_routes.get_telecom_test_evidence(test_id)); return
            self._json(telecom_test_routes.get_telecom_test_status(test_id)); return
        if self.path.startswith("/api/export/"):
            self._handle_export(); return
        self.send_response(404); self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(raw)
        except Exception:
            data = {}

        try:
            if self.path == "/api/telemetry":
                self._json(telemetry_routes.handle_telemetry(data)); return
            if self.path == "/api/telecom-tests/run":
                self._json(telecom_test_routes.handle_run_telecom_test(data, _run_session_thread)); return
            if self.path.startswith("/api/telecom-tests/") and self.path.endswith("/abort"):
                from urllib.parse import unquote
                test_id = unquote(self.path.split("/")[3])
                self._json(telecom_test_routes.handle_abort_telecom_test(test_id)); return
            if self.path == "/api/start":
                self._json(mapper_routes.handle_start(data, _run_session_thread)); return
            if self.path == "/api/prompt":
                self._json(mapper_routes.handle_prompt(data)); return
            if self.path == "/api/inject-dtmf":
                self._json(mapper_routes.handle_inject_dtmf(data)); return
            if self.path == "/api/inject-voice":
                self._json(mapper_routes.handle_inject_voice(data)); return
            if self.path == "/api/end":
                self._json(mapper_routes.handle_end()); return
            if self.path == "/api/set-mode":
                self._json(mapper_routes.handle_set_mode(data)); return
            if self.path == "/api/edit-node":
                self._json(mapper_routes.handle_edit_node(data)); return
            if self.path == "/api/node-notes":
                self._json(mapper_routes.handle_node_notes(data)); return
            if self.path.startswith("/api/maps/"):
                from urllib.parse import unquote
                target = unquote(self.path[len("/api/maps/"):])
                self._json(mapper_routes.handle_maps_save(target, data)); return
            if self.path == "/api/auto-fix":
                self._handle_auto_fix(); return
            if self.path == "/api/test-twilio":
                self._handle_test_twilio(data); return
            if self.path == "/api/suites":
                self._json(run_suite_routes.save_suite(data)); return
            if self.path == "/api/suites/run":
                stream_url_fn = lambda: _to_wss(_detect_ngrok_url() or _default_stream_url)
                self._json(run_suite_routes.run_test_suite(data, stream_url_fn)); return
            if self.path == "/api/run-suites/import":
                self._json(run_suite_routes.import_run_suite(data)); return
            if self.path == "/api/run-suites/save":
                self._json(run_suite_routes.save_run_suite_json(data)); return
            if self.path == "/api/run-suites/abort":
                self._json(run_suite_routes.abort_run_suite()); return
            if self.path.startswith("/api/run-suites/") and self.path.endswith("/run"):
                from urllib.parse import unquote
                suite_id = unquote(self.path[len("/api/run-suites/"):-len("/run")])
                self._json(run_suite_routes.start_run_suite(suite_id, _persistent_stream)); return
        except ValueError as exc:
            self._json_error(400, str(exc)); return
        except FileNotFoundError as exc:
            self._json_error(404, str(exc)); return

        self.send_response(404); self.end_headers()

    def do_DELETE(self) -> None:
        if self.path.startswith("/api/maps/"):
            from urllib.parse import unquote
            target = unquote(self.path[len("/api/maps/"):])
            self._json(mapper_routes.handle_maps_delete(target)); return
        if self.path.startswith("/api/run-suites/"):
            from urllib.parse import unquote
            suite_id = unquote(self.path[len("/api/run-suites/"):])
            try:
                self._json(run_suite_routes.delete_run_suite(suite_id))
            except Exception as exc:
                self._json_error(500, str(exc))
            return
        self.send_response(404); self.end_headers()

    # ── Inline handlers for routes with custom response shapes ────────────────

    def _handle_export(self) -> None:
        from urllib.parse import unquote, urlparse
        parsed = urlparse(self.path)
        parts = parsed.path[len("/api/export/"):].split("/", 1)
        fmt = parts[0]
        target = unquote(parts[1]) if len(parts) > 1 else ""
        if target:
            data = map_store.load_map(target)
            graph = (data or {}).get("graph", {})
        else:
            graph = STATE.graph or (STATE.session.mapper.graph() if STATE.session else {})
        if fmt == "json":
            body = json.dumps({"target": target, "graph": graph}, indent=2).encode("utf-8")
            ctype, fname = "application/json", f"ivr_{target or 'map'}.json"
        elif fmt == "mermaid":
            body = map_store.export_mermaid(graph, target).encode("utf-8")
            ctype, fname = "text/plain; charset=utf-8", f"ivr_{target or 'map'}.mmd"
        elif fmt == "markdown":
            body = map_store.export_markdown(graph, target).encode("utf-8")
            ctype, fname = "text/markdown; charset=utf-8", f"ivr_{target or 'map'}.md"
        else:
            self.send_response(400); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_auto_fix(self) -> None:
        actions: list[str] = []
        ngrok_url = _detect_ngrok_url()
        if not ngrok_url:
            STATE.logs.append("[fix] ngrok not running — attempting to start it")
            result = _start_ngrok_subprocess()
            if result.get("ok"):
                ngrok_url = result["url"]
                actions.append(f"started ngrok at {ngrok_url}")
                STATE.logs.append(f"[fix] ✓ ngrok started: {ngrok_url}")
            else:
                STATE.logs.append(f"[fix] ✗ could not start ngrok: {result.get('error')}")
        self._json({
            "actions": actions,
            "ngrok_url": ngrok_url,
            "stream_url": _to_wss(ngrok_url),
            "diagnose": _diagnose(),
        })

    def _handle_test_twilio(self, data: dict) -> None:
        sid   = data.get("sid")   or os.environ.get("TWILIO_ACCOUNT_SID", "")
        token = data.get("token") or os.environ.get("TWILIO_AUTH_TOKEN", "")
        try:
            from twilio.rest import Client
            client = Client(sid, token)
            account = client.api.accounts(sid).fetch()
            self._json({"ok": True, "friendly_name": account.friendly_name})
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)})

    # ── Response helpers ──────────────────────────────────────────────────────

    def _json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, status_code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _raw(self, status: int, ctype: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        pass  # silence default access logs


# ── Entry point ───────────────────────────────────────────────────────────────

def launch(default_stream_url: str | None = None) -> None:
    global _default_stream_url
    STATE.begin_startup_trace()
    STATE.record_runtime_checkpoint("launch.begin", "launching live map GUI", category="startup")
    _default_stream_url = default_stream_url
    bootstrap = bootstrap_runtime()
    STATE.record_startup_event(
        "bootstrap.ready",
        "runtime bootstrap complete",
        env_method=bootstrap.get("env_method"),
        env_keys_loaded=bootstrap.get("env_keys_loaded"),
        log_level=bootstrap.get("log_level"),
    )
    STATE.record_runtime_checkpoint(
        "bootstrap.ready",
        "runtime bootstrap complete",
        category="startup",
        env_method=bootstrap.get("env_method"),
        env_keys_loaded=bootstrap.get("env_keys_loaded"),
        log_level=bootstrap.get("log_level"),
    )
    logger.info("Launching live map GUI")
    print(f"[DEBUG] Expected stream auth token: {default_stream_auth_token()}")

    _REQUIRED = {
        "TWILIO_ACCOUNT_SID": "place calls",
        "TWILIO_AUTH_TOKEN":  "place calls",
        "TWILIO_PHONE_NUMBER": "caller ID",
        "DEEPGRAM_API_KEY":   "transcription",
    }
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        STATE.record_startup_event("credentials.missing", ",".join(missing))
        print("\n⚠  Missing credentials — add these to your .env file:")
        for k in missing:
            print(f"   {k}  →  needed for {_REQUIRED[k]}")
        print("   See .env.example at the repo root for all options.\n")
    else:
        STATE.record_startup_event("credentials.ready", "all required credentials present")
        print("✓  All required credentials present")

    print(f"Stream server → starting on port {_STREAM_PORT}…")
    if _ensure_stream_server() is not None:
        print(f"Stream server → ✓ ready on :{_STREAM_PORT}")
        EventSink.start()
        from .runtime.runtime_supervisor import supervisor
        supervisor.start()
    else:
        print(f"Stream server → ✗ failed to start on :{_STREAM_PORT}")

    server = HTTPServer(("127.0.0.1", _GUI_PORT), LiveMapRequestHandler)
    STATE.record_startup_event("gui.ready", f"listening on {_GUI_PORT}")
    STATE.record_runtime_checkpoint(
        "gui.ready",
        f"listening on {_GUI_PORT}",
        category="startup",
        port=_GUI_PORT,
    )
    print(f"Live Map GUI  →  http://127.0.0.1:{_GUI_PORT}/")
    if default_stream_url:
        wss = _to_wss(default_stream_url) or ""
        STATE.record_startup_event("stream_url.ready", wss)
        STATE.record_runtime_checkpoint("stream_url.ready", wss, category="startup")
        print(f"Stream URL    →  {wss}  (pre-wired)")
    else:
        STATE.record_startup_event("stream_url.pending", f"expose port {_STREAM_PORT}")
        STATE.record_runtime_checkpoint(
            "stream_url.pending",
            f"expose port {_STREAM_PORT}",
            category="startup",
        )
        print(f"Stream URL    →  expose port {_STREAM_PORT} with: ngrok http {_STREAM_PORT}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(f"http://127.0.0.1:{_GUI_PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        STATE.record_startup_event("shutdown.requested", "keyboard interrupt")
        STATE.record_cleanup_event("shutdown.requested", "keyboard interrupt")
        logger.info("Live map GUI shutdown requested")
        print("\nShutting down.")
