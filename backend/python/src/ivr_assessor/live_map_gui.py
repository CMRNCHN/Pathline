from __future__ import annotations

import json
import os
import queue
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from . import map_store
from .live_map import LiveMappingSession
from .models import CallEvent
from .response_library import ResponseLibrary
from .streaming_server import (
    StreamingServer,
    append_stream_auth_token,
    default_stream_auth_token,
)
from .twilio_client import TwilioTelephonyClient

_STREAM_PORT = 8081
_GUI_PORT = 8080

_SUITES_DIR = Path.home() / ".ivr_assessor" / "suites"

# Persistent streaming server — started once at GUI launch so it's always ready
# when Twilio connects. Sessions just register/clear their callbacks.
_persistent_stream: StreamingServer | None = None


def _normalize_suite_filename(filename: object) -> str:
    """Validate GUI-provided suite filename and return a safe local .json filename."""
    if not isinstance(filename, str):
        raise ValueError("Missing suite filename")

    raw = filename.strip()
    if not raw:
        raise ValueError("Missing suite filename")

    # Disallow directory traversal or nested paths from GUI input.
    if "/" in raw or "\\" in raw:
        raise ValueError("Invalid suite filename")

    if not raw.endswith(".json"):
        raw += ".json"

    name = Path(raw).name
    if name != raw:
        raise ValueError("Invalid suite filename")
    if name.startswith("."):
        raise ValueError("Invalid suite filename")

    stem = Path(name).stem.strip()
    if not stem:
        raise ValueError("Invalid suite filename")

    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if any(ch not in allowed for ch in name):
        raise ValueError("Invalid suite filename")

    return name


def _wait_for_port(host: str, port: int, timeout: float = 8.0) -> bool:
    """Block until the TCP port accepts a connection (or timeout). Returns True if ready."""
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
    import subprocess, os, signal
    try:
        out = subprocess.check_output(["lsof", "-t", f"-i:{port}"], stderr=subprocess.DEVNULL)
        for pid in out.decode().splitlines():
            if pid.strip():
                try:
                    os.kill(int(pid.strip()), signal.SIGKILL)
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
        _free_port(_STREAM_PORT)
        try:
            srv = StreamingServer()
            srv.start_in_background(host="0.0.0.0", port=_STREAM_PORT)
            if not _wait_for_port("127.0.0.1", _STREAM_PORT, timeout=8.0):
                _STATE.logs.append(f"Warning: stream server did not bind to :{_STREAM_PORT} within 8s")
            _persistent_stream = srv
        except Exception as exc:
            _STATE.logs.append(f"Stream server start failed: {exc}")
            return None
    return _persistent_stream


def _detect_ngrok_url() -> str | None:
    """Query ngrok's local API to find the current public URL tunneling to our stream port."""
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=1.5) as r:
            data = json.loads(r.read())
        for tun in data.get("tunnels", []):
            if tun.get("proto") == "https":
                addr = tun.get("config", {}).get("addr", "")
                # Match any ngrok tunnel pointing at our stream port
                if str(_STREAM_PORT) in addr:
                    return tun["public_url"]
        # Fallback: if there's any https tunnel, return it
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
    
    token = force_token if force_token else (_persistent_stream.stream_auth_token if _persistent_stream else default_stream_auth_token())
    return append_stream_auth_token(
        urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment)),
        token=token
    )


def _diagnose() -> dict:
    """Run a full pipeline check and report status of every dependency."""
    issues: list[str] = []
    fixes: list[dict] = []

    # 1. Twilio creds
    twilio = {"ok": False, "account": None, "error": None}
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
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

    # 2. Deepgram API key
    deepgram_key = os.environ.get("DEEPGRAM_API_KEY", "")
    deepgram = {"ok": bool(deepgram_key), "error": None if deepgram_key else "Missing DEEPGRAM_API_KEY"}
    if not deepgram_key:
        issues.append("Deepgram API key missing — transcription will not work (set DEEPGRAM_API_KEY in .env)")

    # 3. Stream server (port 8081 listening)
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

    # 3. ngrok tunnel
    ngrok_url = _detect_ngrok_url()
    ngrok = {
        "running": ngrok_url is not None,
        "url": ngrok_url,
        "expected_port": _STREAM_PORT,
    }
    if not ngrok_url:
        issues.append(f"ngrok is not running — run: ngrok http {_STREAM_PORT}")
        fixes.append({"action": "start_ngrok", "label": f"Start ngrok on :{_STREAM_PORT}"})

    # 5. Stream URL match — does the configured URL match ngrok?
    suggested_wss = _to_wss(ngrok_url) if ngrok_url else None
    return {
        "twilio": twilio,
        "deepgram": deepgram,
        "stream_server": {"listening": stream_listening, "port": _STREAM_PORT},
        "ngrok": ngrok,
        "suggested_stream_url": suggested_wss,
        "issues": issues,
        "fixes": fixes,
        "ok": not issues,
    }


def _start_ngrok_subprocess() -> dict:
    """Try to launch ngrok ourselves if it isn't running. Returns {ok, url, error}."""
    import shutil, subprocess
    binary = shutil.which("ngrok") or "/opt/homebrew/bin/ngrok"
    if not binary or not os.path.exists(binary):
        return {"ok": False, "error": "ngrok binary not found in PATH"}
    try:
        # Don't block the caller; ngrok writes its API to localhost:4040
        subprocess.Popen(
            [binary, "http", str(_STREAM_PORT)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    # Poll for it to come up
    for _ in range(40):
        time.sleep(0.25)
        url = _detect_ngrok_url()
        if url:
            return {"ok": True, "url": url}
    return {"ok": False, "error": "ngrok did not respond within 10s"}


def _poll_call_status(client, call_sid: str) -> None:
    """Background thread: poll Twilio for call.status changes and log them."""
    last_status = None
    poll_count = 0
    while poll_count < 240:  # ~2 minutes max at 0.5s intervals
        try:
            call = client.calls(call_sid).fetch()
            status = call.status
            if status != last_status:
                _STATE.logs.append(f"[twilio] call {call_sid[:10]}… status: {status}")
                last_status = status
                if status in ("completed", "busy", "failed", "no-answer", "canceled"):
                    if call.duration:
                        _STATE.logs.append(f"[twilio] duration: {call.duration}s")
                    return
        except Exception:
            pass
        time.sleep(0.5)
        poll_count += 1


@dataclass
class QueuePromptSource:
    prompt_queue: queue.Queue = field(default_factory=queue.Queue)
    _t_start: float = field(default_factory=time.time)

    def next_event(self, session_id: str) -> CallEvent | None:  # noqa: ARG002
        text = self.prompt_queue.get()
        if text is None:
            return None
        t_ms = int((time.time() - self._t_start) * 1000)
        return CallEvent(kind="prompt", text=text, t_ms=t_ms)

    def elapsed_ms(self) -> int:
        return int((time.time() - self._t_start) * 1000)


class _AppState:
    def __init__(self) -> None:
        self.session: LiveMappingSession | None = None
        self.source: QueuePromptSource | None = None
        self.streaming_server: StreamingServer | None = None
        self.logs: list[str] = []
        self.is_running: bool = False
        self.ledger_idx: int = 0
        self.graph: dict = {}
        self.target: str = ""
        self.start_time: float | None = None
        self.error: str | None = None
        self.live_caption: str = ""

    def reset(self) -> None:
        self.session = None
        self.source = None
        self.streaming_server = None
        self.logs = []
        self.is_running = False
        self.ledger_idx = 0
        self.graph = {}
        self.target = ""
        self.start_time = None
        self.error = None
        self.live_caption = ""

    def drain_logs(self) -> list[str]:
        logs, self.logs = self.logs, []
        return logs

    def active_prompt(self) -> str | None:
        if self.session is None:
            return None
        for evt in reversed(self.session.ledger.all()):
            if evt.kind == "prompt":
                return evt.text
        return None


_STATE = _AppState()


def _run_session_thread(
    target: str,
    user: str,
    sid: str,
    token: str,
    tnum: str,
    stream_url: str | None,
    manual_mode: bool = False,
) -> None:
    _STATE.logs.append(f"[debug] Starting session thread for target: {target}")
    
    # Fallback to the module's default stream URL if the frontend didn't supply one
    stream_url = stream_url or _default_stream_url

    _STATE.logs.append(f"[debug] Input stream_url: {stream_url}")
    try:
        source = QueuePromptSource()
        _STATE.source = source
        _STATE.target = target
        _STATE.start_time = time.time()

        # Ensure the stream server is up first to get its definitive auth token
        active_token = None
        live_ngrok = _detect_ngrok_url()
        if stream_url or live_ngrok:
            srv = _ensure_stream_server()
            _STATE.streaming_server = srv
            active_token = srv.stream_auth_token if srv else default_stream_auth_token()

        # Auto-detect ngrok URL and override any stale one in settings
        if live_ngrok:
            corrected = _to_wss(live_ngrok, force_token=active_token)
            if stream_url and stream_url != corrected:
                _STATE.logs.append(f"[fix] stream URL was '{stream_url}'")
                _STATE.logs.append(f"[fix] using live ngrok URL '{corrected}' instead")
            stream_url = corrected
        elif stream_url:
            stream_url = _to_wss(stream_url, force_token=active_token)
            _STATE.logs.append(f"[warn] ngrok not detected on :4040 — using saved stream URL")
        else:
            _STATE.logs.append("[warn] no stream URL and no ngrok detected — transcription will be disabled")
            
        _STATE.logs.append(f"[debug] Final computed stream_url for Twilio: {stream_url}")

        if stream_url:
            srv = _STATE.streaming_server

            # IVR prompts arrive as multiple is_final chunks (~1-2s each); we
            # accumulate them into one utterance and only push to the prompt
            # queue when speech_final fires (Deepgram's endpointing detected a
            # real pause). Otherwise the mapper sees fragmented half-prompts.
            _utterance: dict[str, list[str]] = {"chunks": []}

            def _flush_utterance() -> None:
                joined = " ".join(_utterance["chunks"]).strip()
                _utterance["chunks"] = []
                if joined:
                    _STATE.logs.append(f"[transcript] {joined}")
                    source.prompt_queue.put(joined)
                _STATE.live_caption = ""

            def _on_transcript(text: str, is_final: bool, speech_final: bool) -> None:
                t = text.strip()
                if not t:
                    if speech_final:
                        _flush_utterance()
                    return

                if is_final:
                    _utterance["chunks"].append(t)
                    _STATE.live_caption = " ".join(_utterance["chunks"])
                    if speech_final:
                        _flush_utterance()
                else:
                    # Interim word-by-word updates only refresh the caption bar;
                    # never appended to logs (used to flood the UI).
                    pending = " ".join(_utterance["chunks"])
                    _STATE.live_caption = (pending + " " + t).strip() if pending else t

            def _on_status(msg: str) -> None:
                _STATE.logs.append(msg)

            if srv:
                srv.clear_callbacks()
                srv.register_transcript_callback(_on_transcript)
                srv.register_status_callback(_on_status)
                _STATE.logs.append(f"[ok] stream server ready on :{_STREAM_PORT}")
                _STATE.logs.append(f"[ok] Twilio will stream to {stream_url}")
                if not os.environ.get("DEEPGRAM_API_KEY"):
                    _STATE.logs.append("[warn] DEEPGRAM_API_KEY not set — transcripts will be disabled")
            else:
                _STATE.logs.append("[error] stream server unavailable — transcription disabled")

        # Pre-load any saved graph for this target so we build on prior knowledge
        existing = map_store.load_map(target)
        prior_graph = existing.get("graph", {}) if existing else {}
        if prior_graph:
            _STATE.logs.append(f"Loaded saved map with {len(prior_graph)} prior nodes")
            _STATE.graph = prior_graph

        telephony = TwilioTelephonyClient(
            account_sid=sid or None,
            auth_token=token or None,
            twilio_number=tnum or None,
            user_phone_number=user or None,
            stream_url=stream_url,
        )

        session = LiveMappingSession(
            target_number=target,
            response_mode="dtmf",
            prompt_source=source,
            telephony=telephony,
            response_library=ResponseLibrary(clips=[]),
            manual_mode=manual_mode,
        )

        _STATE.session = session
        _STATE.logs.append(f"[dial] calling {target}…")

        # session.run() blocks; we need to spawn the call-status poller in a
        # separate thread that hooks the call SID once it's known.
        def _attach_status_poller():
            # Wait briefly for session.session_id to be set by the dial
            for _ in range(40):
                time.sleep(0.1)
                if session.session_id:
                    _STATE.logs.append(f"[twilio] call SID: {session.session_id}")
                    try:
                        _poll_call_status(telephony._client, session.session_id)
                    except Exception:
                        pass
                    return
        threading.Thread(target=_attach_status_poller, daemon=True).start()

        summary = session.run()
        _STATE.graph = summary.graph
        _STATE.logs.append("[ok] session ended cleanly")

        # Auto-save the map for this target
        try:
            map_store.save_map(target, summary.graph)
            _STATE.logs.append(f"Saved map for {target}")
        except Exception as exc:
            _STATE.logs.append(f"Save error: {exc}")

    except Exception as e:
        msg = str(e)
        _STATE.error = msg
        _STATE.logs.append(f"Error: {msg}")
    finally:
        _STATE.is_running = False
        _STATE.session = None
        # Drop our transcript callback so it doesn't leak into the next session
        if _persistent_stream is not None:
            try:
                _persistent_stream.clear_callbacks()
            except Exception:
                pass


# ── HTML ──────────────────────────────────────────────────────────────────────

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IVR Suite — Live Mapper</title>
<style>
@import url('https://rsms.me/inter/inter.css');

:root{
  --bg-0: #0a0d18;--bg-1: #0f1322;--bg-2: #161b2e;--bg-3: #1c2238;
  --border: rgba(255,255,255,.06);--border-strong: rgba(255,255,255,.10);
  --text-1: #eef0f7;--text-2: #a4adc4;--text-3: #6b7693;--text-4: #4a5070;
  --accent: #6e8dff;--accent-soft: rgba(110,141,255,.16);
  --success: #34d399;--success-soft: rgba(52,211,153,.16);
  --warn: #fbbf24;--warn-soft: rgba(251,191,36,.16);
  --danger: #f87171;--danger-soft: rgba(248,113,113,.16);
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100vh;overflow:hidden;font-family:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg-0);color:var(--text-1);font-size:13px;letter-spacing:-.01em}

/* ── HEADER ──────────────────────────────────────────── */
header{height:70px;background:linear-gradient(180deg,#11162a 0%,#0c1020 100%);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:20px;padding:0 24px;flex-shrink:0}
.logo{font-size:15px;font-weight:700;color:#fff;display:flex;align-items:center;gap:10px}
.logo-icon{width:32px;height:32px;border-radius:10px;background:linear-gradient(135deg,#6e8dff 0%,#9d7eff 100%);display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 4px 12px rgba(110,141,255,.4)}
.hdr-field{display:flex;align-items:center;gap:10px;background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:9px;padding:0 16px;height:42px}
.hdr-field label{font-size:10px;font-weight:700;letter-spacing:.6px;color:var(--text-3);text-transform:uppercase}
.hdr-field input{background:transparent;border:none;outline:none;font-size:14px;font-weight:600;color:var(--text-1);width:180px;padding:0}
.hdr-spacer{flex:1}
.hdr-status{font-size:12px;font-weight:600;padding:8px 14px;border-radius:99px;background:var(--warn-soft);color:var(--warn);border:1px solid rgba(251,191,36,.25);display:inline-flex;align-items:center;gap:6px}
.btn-primary{background:linear-gradient(135deg,#34d399 0%,#10b981 100%);color:#fff;border:none;border-radius:9px;padding:0 20px;height:40px;font-size:13px;font-weight:600;cursor:pointer;box-shadow:0 4px 12px rgba(52,211,153,.3);transition:filter .15s}
.btn-primary:hover{filter:brightness(1.08)}
.hdr-btn{width:40px;height:40px;border:1px solid var(--border);background:rgba(255,255,255,.04);border-radius:9px;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s}
.hdr-btn:hover{background:rgba(255,255,255,.07);border-color:var(--border-strong)}

/* ── MAIN LAYOUT ─────────────────────────────────────── */
.root{display:flex;height:calc(100vh - 70px);gap:16px;padding:16px;overflow:hidden}
.center{flex:1;display:flex;flex-direction:column;min-width:0;gap:12px}
.transcript-header{background:linear-gradient(135deg,rgba(110,141,255,.08) 0%,rgba(110,141,255,.04) 100%);border:1px solid var(--accent-soft);border-radius:13px;padding:16px;display:flex;align-items:center;gap:12px}
.transcript-status{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:var(--text-1)}
.status-dot{width:10px;height:10px;border-radius:50%;background:var(--success);box-shadow:0 0 8px var(--success);animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.transcript-duration{margin-left:auto;font-family:'JetBrains Mono','SF Mono',Menlo,monospace;font-size:12px;color:var(--text-3)}
.transcript-box{flex:1;overflow-y:auto;background:var(--bg-0);border:1px solid var(--border);border-radius:13px;padding:20px;font-family:'JetBrains Mono','SF Mono',Menlo,monospace;font-size:13px;line-height:1.8;color:var(--text-2)}
.transcript-box::-webkit-scrollbar{width:8px}
.transcript-box::-webkit-scrollbar-thumb{background:rgba(255,255,255,.08);border-radius:4px}
.log-entry{padding:8px 0;border-bottom:1px solid rgba(255,255,255,.02);word-break:break-word}
.log-entry:last-child{border-bottom:none}
.log-time{color:var(--text-4);font-weight:500;margin-right:12px;min-width:60px}
.log-text{color:var(--text-2)}
.log-text.transcript{color:#38bdf8;font-weight:600}
.log-text.error{color:var(--danger);font-weight:600}
.empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--text-3);text-align:center}
.empty-icon{font-size:48px;margin-bottom:16px}

/* ── LIVE CAPTION ────────────────────────────────────── */
.live-caption-box{background:linear-gradient(90deg,rgba(56,189,248,.1) 0%,rgba(59,130,246,.1) 100%);border:1px solid rgba(56,189,248,.2);border-radius:13px;padding:16px 20px;min-height:60px;display:flex;align-items:center;gap:12px}
.caption-pulse{width:10px;height:10px;border-radius:50%;background:#38bdf8;animation:pulse 1s ease-in-out infinite;flex-shrink:0}
.caption-text{font-family:'JetBrains Mono','SF Mono',Menlo,monospace;font-size:14px;font-weight:500;color:#38bdf8;flex:1;min-height:28px;display:flex;align-items:center}

/* ── GRAPH VISUALIZATION ─────────────────────────────── */
.graph-box{background:var(--bg-1);border:1px solid var(--border);border-radius:13px;padding:16px;font-family:'JetBrains Mono','SF Mono',Menlo,monospace;font-size:12px;line-height:1.6;color:var(--text-2);overflow-y:auto;max-height:400px}
.graph-box::-webkit-scrollbar{width:8px}
.graph-box::-webkit-scrollbar-thumb{background:rgba(255,255,255,.08);border-radius:4px}
.graph-node{padding:8px;margin:4px 0;background:rgba(110,141,255,.08);border-left:3px solid var(--accent);border-radius:6px}
.graph-node.prompt{color:#38bdf8;font-weight:600}
.graph-branch{padding:4px 0 4px 16px;color:var(--text-3);font-size:11px}

/* ── RIGHT SIDEBAR ───────────────────────────────────── */
.sidebar{width:320px;flex-shrink:0;display:flex;flex-direction:column;gap:12px;overflow-y:auto;overflow-x:hidden;padding-right:4px}
.sidebar::-webkit-scrollbar{width:8px}
.sidebar::-webkit-scrollbar-thumb{background:rgba(255,255,255,.08);border-radius:4px}
.control-section{background:var(--bg-1);border:1px solid var(--border);border-radius:13px;padding:16px;display:flex;flex-direction:column;gap:12px}
.section-title{font-size:11px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;color:var(--text-3)}
.smart-input-wrapper{position:relative;display:flex;align-items:center;width:100%}
.smart-input{width:100%;padding:12px 90px 12px 14px;background:var(--bg-2);border:1px solid rgba(110,141,255,.55);border-radius:9px;font-size:13px;font-family:inherit;color:var(--text-1);outline:none;resize:none;height:44px;transition:all .15s}
.smart-input:focus{background:var(--bg-3);border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.smart-input-chip{position:absolute;right:6px;padding:4px 8px;border-radius:6px;font-size:10px;font-weight:600;background:transparent;color:var(--text-3);pointer-events:none;transition:all .15s}
.smart-input-chip.dtmf{background:rgba(110,141,255,.12);color:var(--accent);border-color:rgba(110,141,255,.3)}
.smart-input-chip.speech{background:rgba(168,85,247,.12);color:#a855f7;border-color:rgba(168,85,247,.3)}
.input-hint{font-size:10px;color:var(--text-3);margin-top:-4px;text-align:center}
.send-btn{width:100%;padding:12px;background:linear-gradient(135deg,#6e8dff 0%,#5577ee 100%);color:#fff;border:none;border-radius:9px;font-size:13px;font-weight:600;cursor:pointer;transition:filter .15s;box-shadow:0 2px 6px rgba(110,141,255,.25);margin-top:4px}
.mode-toggle{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;background:var(--bg-2);border:1px solid var(--border);border-radius:9px;cursor:pointer;user-select:none;transition:all .15s}
.mode-toggle:hover{border-color:rgba(110,141,255,.4)}
.mode-toggle-label{font-size:12px;font-weight:600;color:var(--text-1);display:flex;align-items:center;gap:8px}
.mode-toggle-state{font-size:10px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;padding:3px 8px;border-radius:99px;background:rgba(110,141,255,.16);color:var(--accent);border:1px solid rgba(110,141,255,.3)}
.mode-toggle.is-manual .mode-toggle-state{background:var(--bg-3);color:var(--text-3);border-color:var(--border)}
.send-btn:hover{filter:brightness(1.1)}
.keypad{display:grid;grid-template-columns:repeat(3, 1fr);gap:6px;margin-top:8px}
.kbtn{aspect-ratio:1/1;background:var(--bg-2);border:1px solid var(--border);border-radius:9px;font-size:18px;font-weight:600;color:var(--text-1);cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;transition:all .12s;user-select:none}
.kbtn span{font-size:8px;color:var(--text-3);margin-top:2px;font-weight:500}
.kbtn:hover{background:var(--bg-3);border-color:rgba(110,141,255,.3);box-shadow:0 0 0 3px var(--accent-soft)}
.kbtn:active{background:var(--accent-soft);transform:scale(.95)}
.pad-row{display:flex;gap:6px;margin-top:4px}
.pad-display{flex:1;background:var(--bg-2);border:1px solid var(--border);border-radius:9px;padding:12px;text-align:center;font-size:16px;font-weight:600;font-family:'JetBrains Mono';color:var(--text-1);min-height:44px;display:flex;align-items:center;justify-content:center;letter-spacing:3px}
.pad-del,.pad-send{flex:1;padding:12px;border:1px solid var(--border);border-radius:9px;font-size:13px;font-weight:600;cursor:pointer;transition:all .12s;background:var(--bg-2);color:var(--text-1)}
.pad-del{color:var(--danger);border-color:rgba(248,113,113,.2)}
.pad-del:hover{background:var(--danger-soft);border-color:var(--danger)}
.pad-send{background:linear-gradient(135deg,#6e8dff 0%,#5577ee 100%);color:#fff;border:none;font-weight:600;cursor:pointer}
.pad-send:hover{filter:brightness(1.1)}
.status-box{background:linear-gradient(135deg,rgba(52,211,153,.08) 0%,rgba(16,185,129,.08) 100%);border:1px solid rgba(52,211,153,.2);border-radius:13px;padding:12px 14px}
.status-item{display:flex;align-items:center;gap:8px;font-size:12px;padding:4px 0}
.status-indicator{width:8px;height:8px;border-radius:50%;background:var(--success)}
.status-text{color:var(--text-2)}
.status-value{color:var(--text-1);font-weight:600;margin-left:auto}
.info-box{background:var(--bg-2);border:1px solid var(--border);border-radius:13px;padding:12px 14px;font-size:11px;color:var(--text-3);line-height:1.6}

/* ── MODAL ──────────────────────────────────────────── */
.modal{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px)}
.modal-content{background:var(--bg-1);width:900px;height:700px;border-radius:13px;border:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,.5)}
.modal-header{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;background:var(--bg-2)}
.modal-header h2{font-size:15px;font-weight:600;color:#fff}
.modal-close{background:none;border:none;color:var(--text-3);font-size:18px;cursor:pointer}
.modal-close:hover{color:var(--danger)}
.ts-item{padding:10px 12px; border-radius:8px; cursor:pointer; color:var(--text-2); margin-bottom:4px; font-size:13px; transition:all .15s;}
.ts-item:hover{background:rgba(255,255,255,.04);}
.ts-item.active{background:var(--accent-soft); color:var(--accent); font-weight:600;}
.case-card{background:var(--bg-2); border:1px solid var(--border); border-radius:9px; padding:16px; display:flex; flex-direction:column; gap:12px;}
.trigger-block{display:flex;flex-direction:column;gap:4px;margin-top:10px;background:var(--bg-1);border:1px solid var(--border);border-radius:8px;padding:10px;}
.trigger-title-row{display:flex;align-items:center;gap:6px;}
.trigger-title-label{font-size:10px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:var(--text-3);width:36px;flex-shrink:0;}
.trigger-title-input{flex:1;background:transparent;border:none;border-bottom:1px solid var(--border);color:var(--text-1);padding:3px 0;font-size:12px;font-weight:600;outline:none;}
.trigger-title-input:focus{border-bottom-color:var(--accent);}
.trigger-row{display:flex;gap:6px;align-items:center;margin-top:4px;}
.trigger-input{flex:1;background:var(--bg-2);border:1px solid var(--border);border-radius:6px;color:var(--text-1);padding:7px;font-size:12px;outline:none;}
.trigger-input:focus{border-color:var(--accent);}
.trigger-select{background:var(--bg-2);border:1px solid var(--border);border-radius:6px;color:var(--text-1);padding:7px;font-size:12px;outline:none;width:80px;}
.trigger-del{background:none;border:none;color:var(--danger);cursor:pointer;padding:4px;}
.var-section{margin-bottom:16px;}
.var-col-heads{display:grid;grid-template-columns:1fr 120px 1fr 24px;gap:6px;padding:0 2px;margin-top:8px;}
.var-col-head{font-size:10px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:var(--text-3);}
.var-row{display:grid;grid-template-columns:1fr 120px 1fr 24px;gap:6px;align-items:center;margin-top:4px;}
.var-label{background:var(--bg-1);border:1px solid var(--border);border-radius:6px;color:var(--text-1);padding:7px;font-size:12px;outline:none;}
.var-label:focus{border-color:var(--accent);}
.var-key{background:var(--bg-1);border:1px solid var(--border);border-radius:6px;color:var(--accent);padding:7px;font-size:12px;font-weight:600;outline:none;font-family:'JetBrains Mono','SF Mono',monospace;}
.var-key:focus{border-color:var(--accent);}
.var-val{background:var(--bg-1);border:1px solid var(--border);border-radius:6px;color:var(--text-1);padding:7px;font-size:12px;outline:none;}
.var-val:focus{border-color:var(--accent);}
.var-val.filled{border-color:rgba(110,141,255,.4);color:#38bdf8;}
.var-hint{font-size:10px;color:var(--text-3);margin-top:6px;}
.var-hint code{color:var(--accent);background:var(--bg-2);padding:1px 4px;border-radius:3px;font-size:10px;}
.data-loader{background:var(--bg-2);border:1px solid var(--border);border-radius:8px;padding:12px;margin-top:12px;display:flex;flex-direction:column;gap:8px;}
.data-loader-title{font-size:10px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:var(--text-3);}
.data-loader-input{background:var(--bg-1);border:1px solid var(--border);border-radius:6px;color:var(--text-2);padding:8px;font-size:11px;font-family:'JetBrains Mono','SF Mono',monospace;outline:none;resize:none;width:100%;box-sizing:border-box;}
.data-loader-input:focus{border-color:var(--accent);}
.data-loader-row{display:flex;gap:8px;align-items:center;}
.parse-btn{background:linear-gradient(135deg,#6e8dff,#5577ee);color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap;}
.parse-btn:hover{filter:brightness(1.1);}
.parse-status{font-size:11px;color:var(--text-3);}
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-icon">📞</div>
    <div>IVR Suite</div>
  </div>
  <div class="hdr-field">
    <label>Target</label>
    <input id="f-target" type="tel" placeholder="(800) 555-0114" value="">
  </div>
  <div class="hdr-spacer"></div>
  <span class="hdr-status" id="hdr-status">⚠ Idle</span>
  <button class="btn-primary" id="btn-start">📞 Start Call</button>
  <button class="hdr-btn" title="Test Suites" id="btn-test-suite">🧪</button>
  <button class="hdr-btn" title="Settings">⚙️</button>
</header>

<div class="root">
  <!-- CENTER: TRANSCRIPTION & ACTIVITY -->
  <div class="center">
    <div class="transcript-header">
      <div class="transcript-status">
        <span class="status-dot"></span>
        <span>Live Transcription</span>
      </div>
      <div class="transcript-duration" id="timer">00:00</div>
    </div>
    <div class="transcript-box" id="transcript">
      <div class="empty-state">
        <div class="empty-icon">🎙️</div>
        <p>Call activity will appear here</p>
      </div>
    </div>
    <div class="live-caption-box" id="caption-box" style="display:none;">
      <div class="caption-pulse"></div>
      <div class="caption-text" id="caption-text"></div>
    </div>
    <div class="graph-box" id="graph-box">
      <div style="color:var(--text-3);text-align:center;padding:20px;">No nodes discovered yet</div>
    </div>
  </div>

  <!-- RIGHT: CONTROLS -->
  <div class="sidebar">
    <!-- AUTO-PILOT TOGGLE -->
    <div class="control-section">
      <div class="section-title">Mode</div>
      <div class="mode-toggle" id="mode-toggle" title="Auto-pilot lets the mapper choose responses; manual hands control to you.">
        <span class="mode-toggle-label">🤖 <span id="mode-toggle-text">Auto-pilot</span></span>
        <span class="mode-toggle-state" id="mode-toggle-state">ON</span>
      </div>
    </div>

    <!-- SMART INPUT -->
    <div class="control-section">
      <div class="section-title">Input</div>
      <div class="smart-input-wrapper">
        <input id="smart-input" class="smart-input" type="text" placeholder="Enter DTMF or text…">
        <div class="smart-input-chip" id="input-chip">Auto-detect</div>
      </div>
      <div class="input-hint">digits, *, # → DTMF · everything else → speech</div>
      <button class="send-btn">Send ↵</button>
    </div>

    <!-- KEYPAD -->
    <div class="control-section">
      <div class="section-title">Keypad</div>
      <div class="keypad">
        <button class="kbtn">1<span></span></button>
        <button class="kbtn">2<span>ABC</span></button>
        <button class="kbtn">3<span>DEF</span></button>
        <button class="kbtn">4<span>GHI</span></button>
        <button class="kbtn">5<span>JKL</span></button>
        <button class="kbtn">6<span>MNO</span></button>
        <button class="kbtn">7<span>PQRS</span></button>
        <button class="kbtn">8<span>TUV</span></button>
        <button class="kbtn">9<span>WXYZ</span></button>
        <button class="kbtn">*</button>
        <button class="kbtn">0</button>
        <button class="kbtn">#</button>
      </div>
      <div class="pad-row">
        <div class="pad-display" id="pad-display">—</div>
        <button class="pad-del">⌫</button>
        <button class="pad-send">Send</button>
      </div>
    </div>

    <!-- STATUS -->
    <div class="control-section">
      <div class="section-title">Status</div>
      <div class="status-box">
        <div class="status-item">
          <div class="status-indicator"></div>
          <span class="status-text">Connected</span>
          <span class="status-value">—</span>
        </div>
        <div class="status-item">
          <div class="status-indicator"></div>
          <span class="status-text">Audio</span>
          <span class="status-value">—</span>
        </div>
        <div class="status-item">
          <div class="status-indicator"></div>
          <span class="status-text">Transcription</span>
          <span class="status-value">—</span>
        </div>
      </div>
    </div>

    <!-- INFO -->
    <div class="info-box">
      <strong>💡 Tip:</strong> Use keypad for DTMF or type for speech. Auto-detection shows above.
    </div>
  </div>
</div>

<!-- TEST SUITE MODAL -->
<div class="modal" id="ts-modal" style="display:none;">
  <div class="modal-content">
    <div class="modal-header">
      <h2>🧪 Test Suites</h2>
      <button class="modal-close" id="ts-close">✕</button>
    </div>
    <div class="modal-body" style="display:flex; height:calc(100% - 53px);">
      <div style="width:240px; border-right:1px solid var(--border); background:var(--bg-2); display:flex; flex-direction:column;">
        <div style="padding:16px;">
          <button class="btn-primary" id="ts-new-btn" style="width:100%; height:32px; font-size:12px;">+ New Suite</button>
        </div>
        <div id="ts-list" style="flex:1; overflow-y:auto; padding:0 8px;"></div>
      </div>
      <div id="ts-editor" style="flex:1; padding:20px; overflow-y:auto; background:var(--bg-0); display:none;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
          <input type="text" id="ts-filename" placeholder="suite_name" style="background:transparent; border:none; font-size:18px; color:var(--text-1); font-weight:600; outline:none; border-bottom:1px solid var(--border); padding-bottom:4px;">
          <div style="display:flex; gap:10px;">
            <button class="btn-primary" id="ts-run-btn" style="height:32px; font-size:12px; background:linear-gradient(135deg,#6e8dff 0%,#5577ee 100%); box-shadow:none;">▶ Run Suite</button>
            <button class="btn-primary" id="ts-save-btn" style="height:32px; font-size:12px;">💾 Save</button>
          </div>
        </div>
        <div class="control-section" style="margin-bottom:20px;">
          <div class="section-title">Target Number (Fallback)</div>
          <input type="text" id="ts-target" class="smart-input" placeholder="+18005550199">
        </div>
        <div class="control-section var-section" style="margin-bottom:20px;">
          <div style="display:flex;justify-content:space-between;align-items:center;">
            <div class="section-title">Variables</div>
            <button id="ts-add-var" style="background:none;border:1px solid var(--border);color:var(--text-2);border-radius:6px;cursor:pointer;padding:4px 8px;font-size:11px;">+ Add</button>
          </div>
          <div class="var-hint">Reference any variable in a trigger response as <code>$json_key</code></div>
          <div class="var-col-heads">
            <span class="var-col-head">Variable Name</span>
            <span class="var-col-head">JSON Key</span>
            <span class="var-col-head">Value</span>
            <span></span>
          </div>
          <div id="ts-vars-container"></div>
          <div class="data-loader">
            <div class="data-loader-title">⚡ Load from Data Row</div>
            <textarea id="ts-schema" class="data-loader-input" rows="2" placeholder="Paste header row: _id|bin|cc|exp|cvv|zip|name|..."></textarea>
            <div class="data-loader-row">
              <textarea id="ts-datarow" class="data-loader-input" rows="2" placeholder="Paste data row: 001|411111|4111111111111111|12/26|123|90210|John Doe|..." style="flex:1;"></textarea>
              <button class="parse-btn" id="ts-parse-btn">Fill ↵</button>
            </div>
            <div id="ts-parse-status" class="parse-status"></div>
          </div>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <div class="section-title">Test Cases</div>
          <button id="ts-add-case" style="background:none; border:1px solid var(--border); color:var(--text-2); border-radius:6px; cursor:pointer; padding:4px 8px; font-size:11px;">+ Add Case</button>
        </div>
        <div id="ts-cases-container" style="display:flex; flex-direction:column; gap:16px;"></div>
      </div>
    </div>
  </div>
</div>

<script>
let padBuffer = '';
let isRunning = false;
let startTime = null;
let seenLogs = new Set();

function detectInputType(text) {
  const trimmed = text.trim();
  if (!trimmed) return '';
  return /^[\s0-9*#]+$/.test(trimmed) ? 'dtmf' : 'speech';
}

function updateInputChip() {
  const input = document.getElementById('smart-input');
  const chip = document.getElementById('input-chip');
  const type = detectInputType(input.value);
  chip.textContent = type === '' ? 'Auto-detect' : (type === 'dtmf' ? '⚡ DTMF' : '🗣 Speech');
  chip.className = `smart-input-chip ${type}`;
}

function addLog(message) {
  if (seenLogs.has(message)) return;
  seenLogs.add(message);

  const transcript = document.getElementById('transcript');
  if (transcript.querySelector('.empty-state')) {
    transcript.innerHTML = '';
  }
  const entry = document.createElement('div');
  entry.className = 'log-entry';
  const time = new Date().toLocaleTimeString();
  const isTranscript = message.includes('[transcript]');
  const isError = message.includes('[error]') || message.includes('Error');
  const textClass = isTranscript ? 'transcript' : (isError ? 'error' : '');
  entry.innerHTML = `<span class="log-time">${time}</span><span class="log-text ${textClass}">${message.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</span>`;
  transcript.appendChild(entry);
  transcript.scrollTop = transcript.scrollHeight;
}

function renderGraph(graph) {
  const graphBox = document.getElementById('graph-box');

  if (!graph || Object.keys(graph).length === 0) {
    graphBox.innerHTML = '<div style="color:var(--text-3);text-align:center;padding:20px;">No nodes discovered yet</div>';
    return;
  }

  let html = '';
  Object.entries(graph).slice(0, 10).forEach(([prompt, node], idx) => {
    const conf = (node.confidence * 100).toFixed(0);
    const branchCount = Object.keys(node.branches || {}).length;

    html += `<div class="graph-node prompt">[Node ${idx + 1}] ${prompt.slice(0, 60)}${prompt.length > 60 ? '...' : ''}</div>`;

    if (node.branches) {
      Object.entries(node.branches).slice(0, 5).forEach(([branch, obs]) => {
        const nextPrompts = obs.next_prompts ? obs.next_prompts.slice(0, 2).join(' → ') : 'END';
        html += `<div class="graph-branch">→ ${branch}: ${nextPrompts.slice(0, 40)}</div>`;
      });
    }

    html += `<div style="color:var(--text-4);font-size:10px;padding:2px 0;">${conf}% • ${branchCount} branches</div>`;
  });

  graphBox.innerHTML = html || '<div style="color:var(--text-3);">Graph data loading...</div>';
}

async function fetchStatus() {
  try {
    const resp = await fetch('/api/status');
    const data = await resp.json();

    // Update header status
    const statusEl = document.getElementById('hdr-status');
    if (data.error) {
      statusEl.textContent = '❌ ' + data.error.split('\n')[0].slice(0, 20);
      statusEl.style.background = 'var(--danger-soft)';
      statusEl.style.color = 'var(--danger)';
    } else if (data.is_running) {
      statusEl.textContent = '🔴 Active';
      statusEl.style.background = 'rgba(248,113,113,.16)';
      statusEl.style.color = 'var(--danger)';
    } else {
      statusEl.textContent = '⚠ Idle';
      statusEl.style.background = 'var(--warn-soft)';
      statusEl.style.color = 'var(--warn)';
    }

    // Sync auto-pilot toggle from server
    if (typeof data.manual_mode === 'boolean' && data.manual_mode !== manualMode) {
      manualMode = data.manual_mode;
      applyModeUI();
    }

    // Add new logs
    if (data.logs) {
      data.logs.forEach(addLog);
    }

    // Update live caption
    if (data.live_caption) {
      document.getElementById('caption-box').style.display = 'flex';
      document.getElementById('caption-text').textContent = data.live_caption;
    } else {
      document.getElementById('caption-box').style.display = 'none';
    }

    // Update graph
    if (data.graph && Object.keys(data.graph).length > 0) {
      renderGraph(data.graph);
    }

    isRunning = data.is_running;

  } catch(e) {
    console.error('Status fetch error:', e);
  }
}

async function startCall() {
  let target = document.getElementById('f-target').value.trim();
  if (!target) {
    addLog('[error] Please enter a target phone number');
    return;
  }

  // Auto-prepend +1 if not already present
  if (!target.startsWith('+')) {
    target = '+1' + target.replace(/\D/g, '');
  }

  addLog('[system] Starting call to ' + target + '...');

  const btn = document.getElementById('btn-start');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '⏳ Calling...';
  btn.style.opacity = '0.7';

  try {
    const resp = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: target,
        user: '',
        sid: '',
        token: '',
        tnum: '',
        stream_url: null,
        manual_mode: false
      })
    });
    const data = await resp.json();
    if (data.status === 'started') {
      addLog('[ok] Call initiated via backend API');
      startTime = Date.now();
    } else {
      addLog('[error] Backend returned: ' + JSON.stringify(data));
    }
  } catch(e) {
    addLog('[error] ' + e.message);
  } finally {
    setTimeout(() => {
      btn.disabled = false;
      btn.innerHTML = originalText;
      btn.style.opacity = '1';
    }, 2000);
  }
}

async function sendInput() {
  const input = document.getElementById('smart-input');
  const text = input.value.trim();
  if (!text) return;

  const type = detectInputType(text);
  const endpoint = type === 'dtmf' ? '/api/inject-dtmf' : '/api/inject-voice';
  const payload = type === 'dtmf' ? { digits: text } : { text: text };

  try {
    await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    addLog(`[${type.toUpperCase()}] You: ${text}`);
    input.value = '';
    updateInputChip();
  } catch(e) {
    addLog('[error] Failed to send: ' + e.message);
  }
}

document.getElementById('btn-start').addEventListener('click', startCall);
document.getElementById('smart-input').addEventListener('input', updateInputChip);
document.getElementById('smart-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendInput();
  }
});

document.querySelector('.send-btn').addEventListener('click', sendInput);

let manualMode = false;
function applyModeUI() {
  const wrap = document.getElementById('mode-toggle');
  const state = document.getElementById('mode-toggle-state');
  const text = document.getElementById('mode-toggle-text');
  if (manualMode) {
    wrap.classList.add('is-manual');
    state.textContent = 'OFF';
    text.textContent = 'Manual';
  } else {
    wrap.classList.remove('is-manual');
    state.textContent = 'ON';
    text.textContent = 'Auto-pilot';
  }
}
async function toggleMode() {
  const next = !manualMode;
  try {
    const resp = await fetch('/api/set-mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manual_mode: next })
    });
    const data = await resp.json();
    manualMode = !!data.manual_mode;
    applyModeUI();
  } catch(e) {
    addLog('[error] Failed to toggle mode: ' + e.message);
  }
}
document.getElementById('mode-toggle').addEventListener('click', toggleMode);
applyModeUI();

document.querySelectorAll('.keypad .kbtn').forEach(btn => {
  btn.addEventListener('click', () => {
    const digit = btn.textContent.split('\n')[0].trim();
    if (digit) {
      padBuffer += digit;
      document.getElementById('pad-display').textContent = padBuffer;
    }
  });
});

document.querySelector('.pad-del').addEventListener('click', () => {
  padBuffer = padBuffer.slice(0, -1);
  document.getElementById('pad-display').textContent = padBuffer || '—';
});

document.querySelector('.pad-send').addEventListener('click', async () => {
  if (padBuffer) {
    try {
      await fetch('/api/inject-dtmf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ digits: padBuffer })
      });
      addLog(`[DTMF] You: ${padBuffer}`);
      padBuffer = '';
      document.getElementById('pad-display').textContent = '—';
    } catch(e) {
      addLog('[error] DTMF send failed: ' + e.message);
    }
  }
});

// Timer
let seconds = 0;
setInterval(() => {
  if (isRunning) {
    seconds++;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    document.getElementById('timer').textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
}, 1000);

// Load config and set default target
fetch('/api/config').then(r => r.json()).then(cfg => {
  if (cfg.target) {
    // Remove +1 prefix for display
    const display = cfg.target.replace(/^\+1/, '');
    document.getElementById('f-target').value = display;
  }
}).catch(e => console.log('Config load failed:', e));

// --- Test Suites Logic ---
let suites = [];
let currentSuiteFilename = null;

async function loadSuites() {
  const resp = await fetch('/api/suites');
  const data = await resp.json();
  suites = data.suites || [];
  renderSuitesList();
}

function renderSuitesList() {
  const container = document.getElementById('ts-list');
  container.innerHTML = '';
  suites.forEach(s => {
    const el = document.createElement('div');
    el.className = 'ts-item' + (currentSuiteFilename === s.filename ? ' active' : '');
    el.textContent = s.filename;
    el.onclick = () => openSuite(s.filename);
    container.appendChild(el);
  });
}

function openSuite(filename) {
  currentSuiteFilename = filename;
  const suite = suites.find(s => s.filename === filename) || { filename: filename, data: { name: filename.replace('.json',''), target_number: '', cases: [], variables: {}, variable_labels: {} } };
  document.getElementById('ts-editor').style.display = 'block';
  document.getElementById('ts-filename').value = suite.filename.replace('.json','');
  document.getElementById('ts-target').value = suite.data.target_number || '';
  document.getElementById('ts-schema').value = suite.data.data_schema || '';
  document.getElementById('ts-parse-status').textContent = '';
  renderVariables(suite.data.variables || {}, suite.data.variable_labels || {});
  renderCases(suite.data.cases || []);
  renderSuitesList();
}

function renderVariables(vars, labels) {
  // vars: {key: value}, labels: {key: label}
  const container = document.getElementById('ts-vars-container');
  container.innerHTML = '';
  const entries = Object.keys(vars).length
    ? Object.entries(vars)
    : Object.entries(labels || {}).map(([k]) => [k, '']);
  const seen = new Set();
  entries.forEach(([k, v]) => {
    seen.add(k);
    container.appendChild(makeVarRow(labels?.[k] || '', k, v));
  });
  // also add rows for labels without values
  Object.entries(labels || {}).forEach(([k, lbl]) => {
    if (!seen.has(k)) container.appendChild(makeVarRow(lbl, k, ''));
  });
}

function makeVarRow(label='', key='', val='') {
  const esc = s => (s || '').replace(/"/g, '&quot;');
  const row = document.createElement('div');
  row.className = 'var-row';
  row.innerHTML = `
    <input class="var-label" placeholder="Card Number" value="${esc(label)}">
    <input class="var-key" placeholder="cc_num" value="${esc(key)}">
    <input class="var-val${val ? ' filled' : ''}" placeholder="value or auto-filled" value="${esc(val)}">
    <button class="trigger-del" onclick="this.closest('.var-row').remove()">✕</button>`;
  return row;
}

function getVariables() {
  const vars = {}, labels = {};
  document.querySelectorAll('#ts-vars-container .var-row').forEach(row => {
    const lbl = row.querySelector('.var-label').value.trim();
    const k   = row.querySelector('.var-key').value.trim();
    const v   = row.querySelector('.var-val').value.trim();
    if (k) { vars[k] = v; if (lbl) labels[k] = lbl; }
  });
  return { vars, labels };
}

function parseDataRow() {
  const schemaRaw = document.getElementById('ts-schema').value.trim();
  const dataRaw   = document.getElementById('ts-datarow').value.trim();
  const status    = document.getElementById('ts-parse-status');
  if (!schemaRaw || !dataRaw) { status.textContent = 'Paste both header and data row first.'; return; }

  const headers = schemaRaw.split('|').map(h => h.trim());
  const values  = dataRaw.split('|');
  const parsed  = {};
  headers.forEach((h, i) => { if (h) parsed[h] = (values[i] || '').trim(); });

  // Fill matching var-val fields where key matches a parsed column
  let filled = 0;
  document.querySelectorAll('#ts-vars-container .var-row').forEach(row => {
    const k = row.querySelector('.var-key').value.trim();
    if (k && parsed[k] !== undefined) {
      const inp = row.querySelector('.var-val');
      inp.value = parsed[k];
      inp.classList.add('filled');
      filled++;
    }
  });
  status.textContent = filled
    ? `✓ Filled ${filled} variable${filled > 1 ? 's' : ''} from data row.`
    : 'No matching JSON keys found. Check key names match your header columns.';
}

document.getElementById('ts-parse-btn').onclick = parseDataRow;

function renderCases(cases) {
  const container = document.getElementById('ts-cases-container');
  container.innerHTML = '';
  cases.forEach((c, cIdx) => {
    const card = document.createElement('div');
    card.className = 'case-card';

    const hdr = document.createElement('div');
    hdr.style.display = 'flex'; hdr.style.justifyContent = 'space-between';
    hdr.innerHTML = `<input type="text" class="trigger-input" value="${c.name || ''}" placeholder="Case Name" style="font-weight:600; font-size:13px; border:none; background:transparent; padding:0; flex:none; width:200px;">
                     <button class="trigger-del" onclick="deleteCase(${cIdx})">🗑 Remove</button>`;
    card.appendChild(hdr);

    const pathRow = document.createElement('div');
    pathRow.style.display = 'flex'; pathRow.style.gap = '8px'; pathRow.style.alignItems = 'center';
    pathRow.innerHTML = `<span style="font-size:11px; color:var(--text-3); width:80px;">Initial Path</span>
                         <input type="text" class="trigger-input path-input" value="${(c.initial_path || []).join(', ')}" placeholder="e.g. 1, 3, 2">`;
    card.appendChild(pathRow);

    const triggersDiv = document.createElement('div');
    triggersDiv.className = 'triggers-container';
    (c.triggers || []).forEach((t, tIdx) => {
      const tr = document.createElement('div');
      tr.className = 'trigger-block';
      const esc = s => (s || '').replace(/"/g, '&quot;');
      tr.innerHTML = `
        <div class="trigger-title-row">
          <span class="trigger-title-label">Title</span>
          <input type="text" class="trigger-title-input t-title" value="${esc(t.title)}" placeholder="e.g. Account Number">
          <button class="trigger-del" onclick="deleteTrigger(${cIdx}, ${tIdx})" style="margin-left:4px;">✕</button>
        </div>
        <div class="trigger-row">
          <input type="text" class="trigger-input t-phrase" value="${esc(t.phrase)}" placeholder="IVR says… (e.g. account number)">
          <input type="text" class="trigger-input t-resp" value="${esc(t.response)}" placeholder="Reply (or $variable)">
          <select class="trigger-select t-kind">
            <option value="dtmf" ${t.kind === 'dtmf' ? 'selected' : ''}>DTMF</option>
            <option value="speech" ${t.kind === 'speech' ? 'selected' : ''}>Speech</option>
          </select>
        </div>
      `;
      triggersDiv.appendChild(tr);
    });
    card.appendChild(triggersDiv);

    const addTrigBtn = document.createElement('button');
    addTrigBtn.textContent = '+ Add Trigger';
    addTrigBtn.style = 'background:none; border:none; color:var(--accent); font-size:11px; cursor:pointer; text-align:left; margin-top:4px;';
    addTrigBtn.onclick = () => addTrigger(cIdx);
    card.appendChild(addTrigBtn);

    container.appendChild(card);
  });
}

function getEditorData() {
  const filename = document.getElementById('ts-filename').value.trim() || 'new_suite';
  const { vars, labels } = getVariables();
  const schema = document.getElementById('ts-schema').value.trim();
  const data = {
    name: filename,
    target_number: document.getElementById('ts-target').value.trim(),
    variables: vars,
    variable_labels: labels,
    ...(schema && { data_schema: schema }),
    cases: []
  };

  const cards = document.querySelectorAll('.case-card');
  cards.forEach(card => {
    const name = card.querySelector('input[placeholder="Case Name"]').value.trim();
    const pathStr = card.querySelector('.path-input').value.trim();
    const initial_path = pathStr ? pathStr.split(',').map(s => s.trim()).filter(s => s) : [];

    const triggers = [];
    card.querySelectorAll('.trigger-block').forEach(tr => {
      const title = tr.querySelector('.t-title')?.value.trim() || '';
      const phrase = tr.querySelector('.t-phrase').value.trim();
      const response = tr.querySelector('.t-resp').value.trim();
      const kind = tr.querySelector('.t-kind').value;
      const t = { phrase, response, kind };
      if (title) t.title = title;
      triggers.push(t);
    });

    data.cases.push({ name, initial_path, triggers });
  });
  return { filename, data };
}

async function saveSuite() {
  const { filename, data } = getEditorData();
  if (!data.target_number) {
    alert('Please enter a default target number for the suite.');
    return false;
  }
  if (!data.cases.length) {
    alert('Please add at least one test case.');
    return false;
  }
  for (const c of data.cases) {
    if (!c.name) {
      alert('Each test case must have a name.');
      return false;
    }
    for (const t of (c.triggers || [])) {
      if (!t.phrase || !t.response) {
        alert(`Case "${c.name}" has a trigger missing phrase or response.`);
        return false;
      }
    }
  }

  const resp = await fetch('/api/suites', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, data })
  });
  if (!resp.ok) {
    let msg = 'Failed to save suite.';
    try {
      const payload = await resp.json();
      if (payload && payload.error) msg = payload.error;
    } catch (e) {
      // no-op
    }
    alert(msg);
    return false;
  }
  await loadSuites();
  openSuite(filename + (filename.endsWith('.json') ? '' : '.json'));
  return true;
}

async function runSuite() {
  const saved = await saveSuite();
  if (!saved) return;
  const { filename } = getEditorData();
  const fname = filename + (filename.endsWith('.json') ? '' : '.json');
  document.getElementById('ts-modal').style.display = 'none';
  const resp = await fetch('/api/suites/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename: fname })
  });
  if (!resp.ok) {
    let msg = 'Failed to start test suite.';
    try {
      const payload = await resp.json();
      if (payload && payload.error) msg = payload.error;
    } catch (e) {
      // no-op
    }
    addLog('[error] ' + msg);
    alert(msg);
    return;
  }
  addLog(`[system] Test suite ${fname} started in background.`);
}

document.getElementById('btn-test-suite').onclick = () => {
  document.getElementById('ts-modal').style.display = 'flex';
  loadSuites();
};
document.getElementById('ts-close').onclick = () => {
  document.getElementById('ts-modal').style.display = 'none';
};
document.getElementById('ts-new-btn').onclick = () => openSuite('new_suite');
document.getElementById('ts-save-btn').onclick = saveSuite;
document.getElementById('ts-run-btn').onclick = runSuite;
document.getElementById('ts-add-case').onclick = () => {
   const { data } = getEditorData();
   data.cases.push({ name: 'New Case', initial_path: [], triggers: [] });
   renderCases(data.cases);
};
window.deleteCase = (idx) => {
   const { data } = getEditorData();
   data.cases.splice(idx, 1);
   renderCases(data.cases);
};
window.deleteTrigger = (cIdx, tIdx) => {
   const { data } = getEditorData();
   data.cases[cIdx].triggers.splice(tIdx, 1);
   renderCases(data.cases);
};
window.addTrigger = (cIdx) => {
   const { data } = getEditorData();
   data.cases[cIdx].triggers.push({ title: '', phrase: '', response: '', kind: 'dtmf' });
   renderCases(data.cases);
};

document.getElementById('ts-add-var').onclick = () => {
  document.getElementById('ts-vars-container').appendChild(makeVarRow('', '', ''));
};

// Poll status
setInterval(fetchStatus, 500);
fetchStatus();
</script>

</body>
</html>
"""


# ── request handler ───────────────────────────────────────────────────────────

_default_stream_url: str | None = None


class LiveMapRequestHandler(BaseHTTPRequestHandler):
    def _json_error(self, status_code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            self._html(HTML_PAGE)
            return
        if self.path == "/api/status":
            self._json(self._status_payload())
            return
        if self.path == "/api/config":
            active_token = _persistent_stream.stream_auth_token if _persistent_stream else default_stream_auth_token()
            wss = _to_wss(_default_stream_url, force_token=active_token) or ""
            self._json({
                "target":  os.environ.get("TARGET_NUMBER", ""),
                "user":    os.environ.get("USER_PHONE_NUMBER", ""),
                "sid":     os.environ.get("TWILIO_ACCOUNT_SID", ""),
                "token":   "",
                "twilio_token_configured": bool(os.environ.get("TWILIO_AUTH_TOKEN")),
                "tnum":    os.environ.get("TWILIO_PHONE_NUMBER", ""),
                "stream":  wss,
                "stream_auth_token": active_token,
            })
            return
        if self.path == "/api/maps":
            self._json({"maps": map_store.list_maps()})
            return
        if self.path == "/api/diagnose":
            self._json(_diagnose())
            return
        if self.path == "/api/suites":
            _SUITES_DIR.mkdir(parents=True, exist_ok=True)
            suites = []
            for p in _SUITES_DIR.glob("*.json"):
                try:
                    with p.open() as f:
                        suites.append({"filename": p.name, "data": json.load(f)})
                except Exception:
                    pass
            self._json({"suites": suites})
            return
        if self.path.startswith("/api/maps/"):
            from urllib.parse import unquote
            target = unquote(self.path[len("/api/maps/"):])
            data = map_store.load_map(target)
            self._json(data or {"graph": None})
            return
        if self.path.startswith("/api/export/"):
            from urllib.parse import unquote, parse_qs, urlparse
            parsed = urlparse(self.path)
            parts = parsed.path[len("/api/export/"):].split("/", 1)
            fmt = parts[0]
            target = unquote(parts[1]) if len(parts) > 1 else ""
            if target:
                data = map_store.load_map(target)
                graph = (data or {}).get("graph", {})
            else:
                graph = _STATE.graph or (_STATE.session.mapper.graph() if _STATE.session else {})
            if fmt == "json":
                body = json.dumps({"target": target, "graph": graph}, indent=2).encode("utf-8")
                ctype = "application/json"
                fname = f"ivr_{target or 'map'}.json"
            elif fmt == "mermaid":
                body = map_store.export_mermaid(graph, target).encode("utf-8")
                ctype = "text/plain; charset=utf-8"
                fname = f"ivr_{target or 'map'}.mmd"
            elif fmt == "markdown":
                body = map_store.export_markdown(graph, target).encode("utf-8")
                ctype = "text/markdown; charset=utf-8"
                fname = f"ivr_{target or 'map'}.md"
            else:
                self.send_response(400); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404); self.end_headers()

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            data = json.loads(raw)
        except Exception:
            data = {}

        if self.path == "/api/start":
            self._handle_start(data); return
        if self.path == "/api/prompt":
            source = _STATE.source
            if source and data.get("text"):
                source.prompt_queue.put(data["text"])
            self._json({"status": "ok"}); return
        if self.path == "/api/inject-dtmf":
            self._handle_inject_dtmf(data); return
        if self.path == "/api/inject-voice":
            self._handle_inject_voice(data); return
        if self.path == "/api/end":
            source = _STATE.source
            if source:
                source.prompt_queue.put(None)
            session = _STATE.session
            if session and session.session_id:
                try:
                    session.telephony.hangup(session.session_id)
                except Exception:
                    pass
            self._json({"status": "ending"}); return
        if self.path == "/api/auto-fix":
            actions: list[str] = []
            ngrok_url = _detect_ngrok_url()
            if not ngrok_url:
                _STATE.logs.append("[fix] ngrok not running — attempting to start it")
                result = _start_ngrok_subprocess()
                if result.get("ok"):
                    ngrok_url = result["url"]
                    actions.append(f"started ngrok at {ngrok_url}")
                    _STATE.logs.append(f"[fix] ✓ ngrok started: {ngrok_url}")
                else:
                    _STATE.logs.append(f"[fix] ✗ could not start ngrok: {result.get('error')}")
            wss = _to_wss(ngrok_url)
            self._json({
                "actions": actions,
                "ngrok_url": ngrok_url,
                "stream_url": wss,
                "diagnose": _diagnose(),
            })
            return
        if self.path == "/api/test-twilio":
            sid   = data.get("sid")   or os.environ.get("TWILIO_ACCOUNT_SID", "")
            token = data.get("token") or os.environ.get("TWILIO_AUTH_TOKEN", "")
            try:
                from twilio.rest import Client
                client = Client(sid, token)
                account = client.api.accounts(sid).fetch()
                self._json({"ok": True, "friendly_name": account.friendly_name})
            except Exception as exc:
                self._json({"ok": False, "error": str(exc)})
            return
        if self.path.startswith("/api/maps/"):
            from urllib.parse import unquote
            target = unquote(self.path[len("/api/maps/"):])
            graph = data.get("graph", {})
            map_store.save_map(target, graph)
            self._json({"status": "saved"}); return
        if self.path == "/api/edit-node":
            target = data.get("target", "")
            old = data.get("old", "")
            new = data.get("new")
            if target and old:
                map_store.edit_node(target, old, new)
            self._json({"status": "ok"}); return
        if self.path == "/api/set-mode":
            session = _STATE.session
            mode = data.get("manual_mode", False)
            if session is not None:
                session.manual_mode = bool(mode)
                _STATE.logs.append(f"[mode] auto-pilot {'OFF' if mode else 'ON'}")
            self._json({"status": "ok", "manual_mode": bool(mode)}); return
        if self.path == "/api/node-notes":
            target = data.get("target", "")
            prompt = data.get("prompt", "")
            notes = data.get("notes", "")
            ok = map_store.set_node_notes(target, prompt, notes) if target and prompt else False
            self._json({"ok": ok}); return
        if self.path == "/api/suites":
            _SUITES_DIR.mkdir(parents=True, exist_ok=True)
            filename = data.get("filename")
            suite_data = data.get("data")
            try:
                normalized_filename = _normalize_suite_filename(filename)
            except ValueError as exc:
                self._json_error(400, str(exc))
                return
            if not isinstance(suite_data, dict):
                self._json_error(400, "Missing or invalid suite data")
                return

            from .test_suite import validate_suite_payload

            try:
                normalized = validate_suite_payload(suite_data)
            except ValueError as exc:
                self._json_error(400, str(exc))
                return

            with (_SUITES_DIR / normalized_filename).open("w") as f:
                json.dump(normalized, f, indent=2)
            self._json({"status": "ok"})
            return
        if self.path == "/api/suites/run":
            filename = data.get("filename")
            try:
                normalized_filename = _normalize_suite_filename(filename)
            except ValueError as exc:
                self._json_error(400, str(exc))
                return
            suite_path = _SUITES_DIR / normalized_filename
            if not suite_path.exists():
                self._json_error(404, f"Suite not found: {normalized_filename}")
                return

            def _run_suite():
                from .test_suite import run_test_suite_from_file, save_suite_result
                from .twilio_client import TwilioTelephonyClient
                sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
                token = os.environ.get("TWILIO_AUTH_TOKEN", "")
                tnum = os.environ.get("TWILIO_PHONE_NUMBER", "")
                user = os.environ.get("USER_PHONE_NUMBER", "")

                runner = None
                if sid and token:
                    runner = TwilioTelephonyClient(
                        account_sid=sid, auth_token=token, twilio_number=tnum,
                        user_phone_number=user, stream_url=_to_wss(_detect_ngrok_url() or _default_stream_url)
                    )
                _STATE.logs.append(f"[test-suite] Starting suite: {normalized_filename}")
                try:
                    result = run_test_suite_from_file(suite_path, runner=runner)
                    json_path, md_path = save_suite_result(result)
                    _STATE.logs.append(f"[test-suite] Finished {normalized_filename}. Passed: {result.passed_cases}/{result.total_cases}")
                    _STATE.logs.append(f"[test-suite] Report saved to: {md_path.name}")
                except Exception as e:
                    _STATE.logs.append(f"[error] Test suite failed: {e}")

            threading.Thread(target=_run_suite, daemon=True).start()
            self._json({"status": "started"})
            return
        self.send_response(404); self.end_headers()

    def do_DELETE(self) -> None:
        if self.path.startswith("/api/maps/"):
            from urllib.parse import unquote
            target = unquote(self.path[len("/api/maps/"):])
            ok = map_store.delete_map(target)
            self._json({"deleted": ok}); return
        self.send_response(404); self.end_headers()

    # ── handlers ──────────────────────────────────────────────────────────────

    def _handle_start(self, data: dict) -> None:
        _STATE.logs.append(f"[debug] /api/start payload: {data}")
        if not _STATE.is_running:
            _STATE.reset()
            _STATE.is_running = True
            threading.Thread(
                target=_run_session_thread,
                args=(
                    data.get("target", ""),
                    data.get("user", ""),
                    data.get("sid", ""),
                    data.get("token", ""),
                    data.get("tnum", ""),
                    data.get("stream_url") or None,
                    bool(data.get("manual_mode", False)),
                ),
                daemon=True,
            ).start()
        self._json({"status": "started"})

    def _handle_inject_dtmf(self, data: dict) -> None:
        session = _STATE.session
        source = _STATE.source
        if session and session.session_id and data.get("digits"):
            try:
                session.telephony.send_dtmf(session.session_id, data["digits"])
                t_ms = source.elapsed_ms() if source else 0
                session._record_event(
                    CallEvent(kind="action", text=f"dtmf:{data['digits']}", t_ms=t_ms),
                    branch_confidence=1.0,
                )
                _STATE.logs.append(f"[dtmf] {data['digits']}")
            except Exception as e:
                _STATE.logs.append(f"DTMF error: {e}")
        self._json({"status": "ok"})

    def _handle_inject_voice(self, data: dict) -> None:
        session = _STATE.session
        source = _STATE.source
        if session and session.session_id and data.get("text"):
            try:
                session.telephony.say(session.session_id, data["text"])
                t_ms = source.elapsed_ms() if source else 0
                session._record_event(
                    CallEvent(kind="action", text=f"say:{data['text']}", t_ms=t_ms),
                    branch_confidence=1.0,
                )
                _STATE.logs.append(f"[say] {data['text']}")
            except Exception as e:
                _STATE.logs.append(f"Voice error: {e}")
        self._json({"status": "ok"})

    def _status_payload(self) -> dict:
        new_logs = _STATE.drain_logs()
        session = _STATE.session
        if session:
            events = session.ledger.all()
            idx = _STATE.ledger_idx
            while idx < len(events):
                evt = events[idx]
                prefix = "[transcript]" if evt.kind == "prompt" else f"[{evt.kind}]"
                new_logs.append(f"{prefix} {evt.text}")
                idx += 1
            _STATE.ledger_idx = idx
        graph = session.mapper.graph() if session else _STATE.graph
        return {
            "is_running": _STATE.is_running,
            "session_ended": not _STATE.is_running and not session,
            "logs": new_logs,
            "graph": graph,
            "active_prompt": _STATE.active_prompt(),
            "live_caption": _STATE.live_caption,
            "error": _STATE.error,
            "manual_mode": bool(session.manual_mode) if session else False,
        }

    def _html(self, content: str) -> None:
        page = content
        if _default_stream_url:
            wss = _to_wss(_default_stream_url) or ""
            page = page.replace("__DEFAULT_STREAM_URL__", wss)
        else:
            page = page.replace("__DEFAULT_STREAM_URL__", "")
        body = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # silence default access logs
        pass


def launch(default_stream_url: str | None = None) -> None:
    global _default_stream_url
    _default_stream_url = default_stream_url
    print(f"[DEBUG] Expected stream auth token: {default_stream_auth_token()}")

    # Credential check — print a clear summary so missing keys are obvious at startup.
    _REQUIRED = {
        "TWILIO_ACCOUNT_SID": "place calls",
        "TWILIO_AUTH_TOKEN": "place calls",
        "TWILIO_PHONE_NUMBER": "caller ID",
        "DEEPGRAM_API_KEY": "transcription",
    }
    missing = [k for k in _REQUIRED if not os.environ.get(k)]
    if missing:
        print("\n⚠  Missing credentials — add these to your .env file:")
        for k in missing:
            print(f"   {k}  →  needed for {_REQUIRED[k]}")
        print("   See .env.example at the repo root for all options.\n")
    else:
        print("✓  All required credentials present")

    # Pre-warm the streaming server so transcription is ready BEFORE the first dial.
    # If we wait until the user clicks Start, Twilio may connect before uvicorn binds
    # and miss the IVR's opening prompt.
    print(f"Stream server → starting on port {_STREAM_PORT}…")
    if _ensure_stream_server() is not None:
        print(f"Stream server → ✓ ready on :{_STREAM_PORT}")
    else:
        print(f"Stream server → ✗ failed to start on :{_STREAM_PORT}")

    server = HTTPServer(("127.0.0.1", _GUI_PORT), LiveMapRequestHandler)
    print(f"Live Map GUI  →  http://127.0.0.1:{_GUI_PORT}/")
    if default_stream_url:
        wss = _to_wss(default_stream_url) or ""
        print(f"Stream URL    →  {wss}  (pre-wired)")
    else:
        print(f"Stream URL    →  expose port {_STREAM_PORT} with: ngrok http {_STREAM_PORT}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(f"http://127.0.0.1:{_GUI_PORT}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
