"""Mapper API route handlers.

Each function receives the parsed request body (data: dict) plus any
infrastructure callables it needs, and returns a response dict.
Raise ValueError for 400 errors, FileNotFoundError for 404 errors.
"""
from __future__ import annotations

import os
import threading
from typing import Callable

from ... import map_store
from ...models import CallEvent
from ..ui.ui_state import STATE


# ── GET handlers ──────────────────────────────────────────────────────────────

def build_status_payload() -> dict:
    new_logs = STATE.drain_logs()
    session = STATE.session
    if session:
        events = session.ledger.all()
        idx = STATE.ledger_idx
        while idx < len(events):
            evt = events[idx]
            prefix = "[transcript]" if evt.kind == "prompt" else f"[{evt.kind}]"
            new_logs.append(f"{prefix} {evt.text}")
            idx += 1
        STATE.ledger_idx = idx
    graph = session.mapper.graph() if session else STATE.graph
    return {
        "is_running": STATE.is_running,
        "session_ended": not STATE.is_running and not session,
        "logs": new_logs,
        "graph": graph,
        "active_prompt": STATE.active_prompt(),
        "live_caption": STATE.live_caption,
        "error": STATE.error,
        "manual_mode": bool(session.manual_mode) if session else False,
    }


def get_config(default_stream_url: str | None, persistent_stream: object, to_wss_fn: Callable, default_token_fn: Callable) -> dict:
    active_token = persistent_stream.stream_auth_token if persistent_stream else default_token_fn()
    wss = to_wss_fn(default_stream_url, force_token=active_token) or ""
    return {
        "target":  os.environ.get("TARGET_NUMBER", ""),
        "user":    os.environ.get("USER_PHONE_NUMBER", ""),
        "sid":     os.environ.get("TWILIO_ACCOUNT_SID", ""),
        "token":   "",
        "twilio_token_configured": bool(os.environ.get("TWILIO_AUTH_TOKEN")),
        "tnum":    os.environ.get("TWILIO_PHONE_NUMBER", ""),
        "stream":  wss,
        "stream_auth_token": active_token,
    }


def get_maps() -> dict:
    return {"maps": map_store.list_maps()}


def get_map(target: str) -> dict:
    data = map_store.load_map(target)
    return data or {"graph": None}


# ── POST handlers ─────────────────────────────────────────────────────────────

def handle_start(data: dict, session_thread_fn: Callable) -> dict:
    STATE.logs.append(f"[debug] /api/start payload: {data}")
    if not STATE.is_running:
        STATE.reset()
        STATE.is_running = True
        threading.Thread(
            target=session_thread_fn,
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
    return {"status": "started"}


def handle_prompt(data: dict) -> dict:
    source = STATE.source
    if source and data.get("text"):
        source.prompt_queue.put(data["text"])
    return {"status": "ok"}


def handle_inject_dtmf(data: dict) -> dict:
    session = STATE.session
    source = STATE.source
    if session and session.session_id and data.get("digits"):
        try:
            session.telephony.send_dtmf(session.session_id, data["digits"])
            t_ms = source.elapsed_ms() if source else 0
            session._record_event(
                CallEvent(kind="action", text=f"dtmf:{data['digits']}", t_ms=t_ms),
                branch_confidence=1.0,
            )
            STATE.logs.append(f"[dtmf] {data['digits']}")
        except Exception as e:
            STATE.logs.append(f"DTMF error: {e}")
    return {"status": "ok"}


def handle_inject_voice(data: dict) -> dict:
    session = STATE.session
    source = STATE.source
    if session and session.session_id and data.get("text"):
        try:
            session.telephony.say(session.session_id, data["text"])
            t_ms = source.elapsed_ms() if source else 0
            session._record_event(
                CallEvent(kind="action", text=f"say:{data['text']}", t_ms=t_ms),
                branch_confidence=1.0,
            )
            STATE.logs.append(f"[say] {data['text']}")
        except Exception as e:
            STATE.logs.append(f"Voice error: {e}")
    return {"status": "ok"}


def handle_end() -> dict:
    source = STATE.source
    if source:
        source.prompt_queue.put(None)
    session = STATE.session
    if session and session.session_id:
        try:
            session.telephony.hangup(session.session_id)
        except Exception:
            pass
    return {"status": "ending"}


def handle_set_mode(data: dict) -> dict:
    session = STATE.session
    mode = data.get("manual_mode", False)
    if session is not None:
        session.manual_mode = bool(mode)
        STATE.logs.append(f"[mode] auto-pilot {'OFF' if mode else 'ON'}")
    return {"status": "ok", "manual_mode": bool(mode)}


def handle_maps_save(target: str, data: dict) -> dict:
    map_store.save_map(target, data.get("graph", {}))
    return {"status": "saved"}


def handle_maps_delete(target: str) -> dict:
    ok = map_store.delete_map(target)
    return {"deleted": ok}


def handle_edit_node(data: dict) -> dict:
    target = data.get("target", "")
    old = data.get("old", "")
    new = data.get("new")
    if target and old:
        map_store.edit_node(target, old, new)
    return {"status": "ok"}


def handle_node_notes(data: dict) -> dict:
    target = data.get("target", "")
    prompt = data.get("prompt", "")
    notes = data.get("notes", "")
    ok = map_store.set_node_notes(target, prompt, notes) if target and prompt else False
    return {"ok": ok}
