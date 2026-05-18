"""Run suite and test suite API route handlers.

Each function returns a response dict.
Raise ValueError for 400 errors, FileNotFoundError for 404 errors.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Callable

from analyst.backend.ui.ui_state import RS_STATE, STATE, RUN_SUITES_DIR, SUITES_DIR


# ── Filename validation ───────────────────────────────────────────────────────

def normalize_suite_filename(filename: object) -> str:
    """Validate and return a safe local .json filename. Raises ValueError on invalid input."""
    if not isinstance(filename, str):
        raise ValueError("Missing suite filename")
    raw = filename.strip()
    if not raw:
        raise ValueError("Missing suite filename")
    if "/" in raw or "\\" in raw:
        raise ValueError("Invalid suite filename")
    if not raw.endswith(".json"):
        raw += ".json"
    name = Path(raw).name
    if name != raw or name.startswith("."):
        raise ValueError("Invalid suite filename")
    if not Path(name).stem.strip():
        raise ValueError("Invalid suite filename")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
    if any(ch not in allowed for ch in name):
        raise ValueError("Invalid suite filename")
    return name


# ── Test suite (legacy editor) — GET / POST ───────────────────────────────────

def list_suites() -> dict:
    SUITES_DIR.mkdir(parents=True, exist_ok=True)
    suites = []
    for p in SUITES_DIR.glob("*.json"):
        try:
            with p.open() as f:
                suites.append({"filename": p.name, "data": json.load(f)})
        except Exception:
            pass
    return {"suites": suites}


def save_suite(data: dict) -> dict:
    SUITES_DIR.mkdir(parents=True, exist_ok=True)
    filename = normalize_suite_filename(data.get("filename"))
    suite_data = data.get("data")
    if not isinstance(suite_data, dict):
        raise ValueError("Missing or invalid suite data")
    from tests.test_suite import validate_suite_payload
    normalized = validate_suite_payload(suite_data)
    with (SUITES_DIR / filename).open("w") as f:
        json.dump(normalized, f, indent=2)
    return {"status": "ok"}


def run_test_suite(data: dict, stream_url_fn: Callable) -> dict:
    filename = normalize_suite_filename(data.get("filename"))
    suite_path = SUITES_DIR / filename
    if not suite_path.exists():
        raise FileNotFoundError(f"Suite not found: {filename}")

    def _run():
        from tests.test_suite import run_test_suite_from_file, save_suite_result
        from runtime.twilio_client import TwilioTelephonyClient
        sid   = os.environ.get("TWILIO_ACCOUNT_SID", "")
        token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        tnum  = os.environ.get("TWILIO_PHONE_NUMBER", "")
        user  = os.environ.get("USER_PHONE_NUMBER", "")
        runner = None
        if sid and token:
            runner = TwilioTelephonyClient(
                account_sid=sid, auth_token=token, twilio_number=tnum,
                user_phone_number=user, stream_url=stream_url_fn(),
            )
        STATE.logs.append(f"[test-suite] Starting suite: {filename}")
        try:
            result = run_test_suite_from_file(suite_path, runner=runner)
            _, md_path = save_suite_result(result)
            STATE.logs.append(f"[test-suite] Finished {filename}. Passed: {result.passed_cases}/{result.total_cases}")
            STATE.logs.append(f"[test-suite] Report saved to: {md_path.name}")
        except Exception as e:
            STATE.logs.append(f"[error] Test suite failed: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started"}


# ── Run suites (new runner) — GET / POST / DELETE ─────────────────────────────

def list_run_suites() -> dict:
    from ...run_suites.loader import list_suites as _list
    return {"suites": _list(suites_dir=RUN_SUITES_DIR)}


def poll_run_suite(suite_id: str) -> dict:  # noqa: ARG001
    events = RS_STATE.poll()
    runner = RS_STATE.get_runner()
    result_dict = None
    if runner and runner.run_result:
        result_dict = runner.run_result.as_dict()
    return {"events": events, "result": result_dict}


def import_run_suite(data: dict) -> dict:
    from ...run_suites.loader import import_suite_json, save_suite as _save
    raw = data.get("json", "")
    if not raw:
        raise ValueError("Missing 'json' field")
    suite = import_suite_json(raw if isinstance(raw, str) else json.dumps(raw))
    _save(suite, suites_dir=RUN_SUITES_DIR)
    return {"status": "ok", "suite_id": suite.suite_id, "name": suite.name}


def save_run_suite_json(data: dict) -> dict:
    from ...run_suites.loader import import_suite_json, save_suite as _save
    raw = data.get("json", "")
    if not raw:
        raise ValueError("Missing 'json' field")
    suite = import_suite_json(raw if isinstance(raw, str) else json.dumps(raw))
    path = _save(suite, suites_dir=RUN_SUITES_DIR)
    return {"status": "saved", "suite_id": suite.suite_id, "file": path.name}


def start_run_suite(suite_id: str, persistent_stream: object) -> dict:
    from ...run_suites.loader import load_suite
    from tests.run_suites.runner import SuiteRunner
    try:
        suite = load_suite(suite_id, suites_dir=RUN_SUITES_DIR)
    except FileNotFoundError:
        raise FileNotFoundError(f"Run suite not found: {suite_id}")

    runner = SuiteRunner(suite=suite, telephony=None)
    if persistent_stream:
        def _transcript_bridge(text: str, is_final: bool, speech_final: bool) -> None:
            r = RS_STATE.get_runner()
            if r:
                r.push_transcript(text, is_final, speech_final)
        persistent_stream.register_transcript_callback(_transcript_bridge)

    RS_STATE.set_runner(runner)
    run_id = runner.start()
    STATE.logs.append(f"[run-suite] Started suite {suite_id!r} run_id={run_id}")
    return {"status": "started", "run_id": run_id, "suite_id": suite_id}


def abort_run_suite() -> dict:
    RS_STATE.abort()
    return {"status": "aborted"}


def delete_run_suite(suite_id: str) -> dict:
    from ...run_suites.loader import delete_suite
    delete_suite(suite_id, suites_dir=RUN_SUITES_DIR)
    return {"deleted": True, "suite_id": suite_id}