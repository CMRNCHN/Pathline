"""SMS bridge: text a number to map, get the summary back as a text.

Twilio inbound SMS webhook -> enqueue a mapping job -> reply when done.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

E164 = re.compile(r"\+?\d{10,15}")


@dataclass
class Job:
    id: str
    requester: str
    target: str
    status: str = "running"  # running | done | error
    summary: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class AppState:
    allowed: set[str]
    twilio_sid: str
    twilio_token: str
    twilio_number: str
    user_phone_number: str | None
    public_base_url: str | None
    reports_dir: Path
    validate_signature: bool = True
    jobs: dict[str, Job] = field(default_factory=dict)


def _twiml(message: str) -> Response:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{message}</Message></Response>"
    )
    return Response(content=body, media_type="application/xml")


def _normalize_number(raw: str) -> str | None:
    match = E164.search(raw)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) == 10:
        digits = "1" + digits
    return "+" + digits


def _format_summary(summary: dict[str, Any]) -> str:
    target = summary.get("target_number", "?")
    graph = summary.get("graph") or {}
    events = summary.get("events") or []
    prompts = sum(1 for e in events if e.get("kind") == "prompt")
    last = summary.get("last_action") or "n/a"
    return (
        f"Mapped {target}\n"
        f"Nodes: {len(graph)} | Prompts heard: {prompts}\n"
        f"Last action: {last}"
    )


async def _run_mapping_job(state: AppState, job: Job) -> None:
    from .call_template import TemplateStyle  # noqa: F401  (ensures package is loaded)
    from .cli import _run_single_session

    loop = asyncio.get_running_loop()
    try:
        summary = await loop.run_in_executor(
            None,
            lambda: _run_single_session(
                target_number=job.target,
                response_mode="dtmf",
                prompt=[],
                response_label="general",
                response_style=None,
                response_clip=[],
                mode="interactive",
                twilio_account_sid=state.twilio_sid,
                twilio_auth_token=state.twilio_token,
                twilio_phone_number=state.twilio_number,
                user_phone_number=state.user_phone_number,
            ),
        )
        payload = summary.as_dict() if hasattr(summary, "as_dict") else dict(summary)
        job.summary = payload
        job.status = "done"
        report_path = state.reports_dir / f"{job.id}.json"
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        job.status = "error"
        job.error = str(exc)

    await _send_completion_sms(state, job)


async def _send_completion_sms(state: AppState, job: Job) -> None:
    try:
        from twilio.rest import Client
    except ImportError:
        return

    if job.status == "done" and job.summary is not None:
        body = _format_summary(job.summary)
        if state.public_base_url:
            body += f"\nReport: {state.public_base_url.rstrip('/')}/reports/{job.id}"
    else:
        body = f"Mapping {job.target} failed: {job.error or 'unknown error'}"

    def _send() -> None:
        client = Client(state.twilio_sid, state.twilio_token)
        client.messages.create(to=job.requester, from_=state.twilio_number, body=body[:1500])

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _send)


async def _verify_twilio_signature(state: AppState, request: Request) -> bool:
    if not state.validate_signature:
        return True
    try:
        from twilio.request_validator import RequestValidator
    except ImportError:
        return False

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    if state.public_base_url:
        path = request.url.path
        if request.url.query:
            path += f"?{request.url.query}"
        url = state.public_base_url.rstrip("/") + path
    else:
        url = str(request.url)

    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    return RequestValidator(state.twilio_token).validate(url, params, signature)


def create_app(state: AppState) -> FastAPI:
    app = FastAPI(title="IVR Assessor SMS bridge")

    @app.post("/sms")
    async def inbound_sms(
        request: Request,
        From: str = Form(...),
        Body: str = Form(""),
    ) -> Response:
        if not await _verify_twilio_signature(state, request):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        if From not in state.allowed:
            return _twiml("Not authorized.")

        text = (Body or "").strip()
        if not text or text.lower() in {"help", "?"}:
            return _twiml("Send a phone number to map (e.g. +18005551234).")

        if text.lower().startswith("status"):
            running = [j for j in state.jobs.values() if j.status == "running"]
            if not running:
                return _twiml("No jobs running.")
            return _twiml(f"{len(running)} job(s) running.")

        target = _normalize_number(text)
        if not target:
            return _twiml("Couldn't parse a phone number. Try +18005551234.")

        job = Job(id=uuid.uuid4().hex[:8], requester=From, target=target)
        state.jobs[job.id] = job
        asyncio.create_task(_run_mapping_job(state, job))

        return _twiml(f"Mapping {target} (job {job.id}). I'll text the summary when done.")

    @app.get("/reports/{job_id}", response_class=HTMLResponse)
    async def report(job_id: str) -> HTMLResponse:
        job = state.jobs.get(job_id)
        if not job or job.summary is None:
            raise HTTPException(status_code=404, detail="Report not found")
        body = json.dumps(job.summary, indent=2, sort_keys=True)
        return HTMLResponse(
            f"<html><body><h2>IVR map: {job.target}</h2><pre>{body}</pre></body></html>"
        )

    @app.get("/healthz", response_class=PlainTextResponse)
    async def healthz() -> str:
        return "ok"

    return app


def build_state_from_env() -> AppState:
    def _required(key: str) -> str:
        value = os.environ.get(key)
        if not value:
            raise RuntimeError(f"Missing required env var: {key}")
        return value

    allowed_raw = os.environ.get("SMS_ALLOWED_NUMBERS", "")
    allowed = {n.strip() for n in allowed_raw.split(",") if n.strip()}
    if not allowed:
        fallback = os.environ.get("USER_PHONE_NUMBER", "").strip()
        if fallback:
            allowed = {fallback}
        else:
            raise RuntimeError(
                "SMS_ALLOWED_NUMBERS (or USER_PHONE_NUMBER) must list at least one E.164 number"
            )

    reports_dir = Path(os.environ.get("SMS_REPORTS_DIR", "/tmp/ivr-reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)

    return AppState(
        allowed=allowed,
        twilio_sid=_required("TWILIO_ACCOUNT_SID"),
        twilio_token=_required("TWILIO_AUTH_TOKEN"),
        twilio_number=_required("TWILIO_PHONE_NUMBER"),
        user_phone_number=os.environ.get("USER_PHONE_NUMBER"),
        public_base_url=os.environ.get("SMS_PUBLIC_BASE_URL"),
        reports_dir=reports_dir,
    )
