"""runtime/telephony/twilio_client.py — Twilio call-control client.

Home of TwilioTelephonyClient, the live-call adapter that satisfies the
TelephonyClient protocol (dial / send_dtmf / play_clip / say / hangup). It is
constructed via runtime.telephony.build_telephony() when TELEPHONY_MODE=twilio,
and directly by CLI/GUI flows with explicit credentials.

This is distinct from runtime/telephony/twilio_media_client.py, which holds the
Media Streams WebSocket client (TwilioMediaClient) used by session_manager.
"""
from __future__ import annotations

import os
import random
from typing import Any
from xml.sax.saxutils import escape, quoteattr


def pick_caller_id(twilio_number: str | None = None) -> str:
    """Return a random number from TWILIO_PHONE_NUMBERS pool, or fall back to TWILIO_PHONE_NUMBER."""
    pool_raw = os.environ.get("TWILIO_PHONE_NUMBERS", "")
    pool = [n.strip() for n in pool_raw.split(",") if n.strip()]
    if pool:
        return random.choice(pool)
    return twilio_number or os.environ.get("TWILIO_PHONE_NUMBER", "")


class TwilioTelephonyClient:
    """A telephony client that uses the Twilio API for live calls."""

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        twilio_number: str | None = None,
        user_phone_number: str | None = None,
        stream_url: str | None = None,
        recording_status_callback: str | None = None,
    ) -> None:
        try:
            from twilio.rest import Client
        except ImportError as exc:
            raise ImportError("Twilio client not installed. Please run 'pip install twilio'.") from exc

        self._sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
        self._token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
        self._from = pick_caller_id(twilio_number)
        self._user_phone_number = user_phone_number
        self._stream_url = stream_url
        self._recording_status_callback = recording_status_callback or os.environ.get("TWILIO_RECORDING_STATUS_CALLBACK")
        self._sessions: dict[str, str] = {}  # session_id -> conference_name

        if not all([self._sid, self._token, self._from]):
            raise ValueError(
                "Twilio credentials not found. Set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER environment variables."
            )

        self._client = Client(self._sid, self._token)

    def dial(self, target_number: str) -> str:
        """Dials the target number and returns a call SID."""
        # Re-pick caller ID each call so a pool rotates across cases in a suite.
        caller = pick_caller_id(self._from)
        if caller != self._from:
            import logging
            logging.getLogger(__name__).info("[caller-id] using %s", caller)
        self._from = caller

        if self._user_phone_number:
            import uuid
            conference_name = f"ivr-{uuid.uuid4().hex[:8]}"
            # IVR leg: <Start><Stream> is non-blocking so the call also joins the conference.
            # <Connect><Stream> is terminal and would prevent <Dial> from executing.
            stream_start = ""
            if self._stream_url:
                stream_start = f'<Start><Stream url={quoteattr(self._stream_url)} /></Start>'
            ivr_twiml = f'<Response>{stream_start}<Dial><Conference record="record-from-start">{escape(conference_name)}</Conference></Dial></Response>'

            kwargs: dict[str, Any] = {"to": target_number, "from_": self._from, "twiml": ivr_twiml, "record": True}
            if self._recording_status_callback:
                kwargs["recording_status_callback"] = self._recording_status_callback
                kwargs["recording_status_callback_event"] = ["completed"]

            user_twiml = f'<Response><Dial><Conference>{escape(conference_name)}</Conference></Dial></Response>'
            self._client.calls.create(to=self._user_phone_number, from_=self._from, twiml=user_twiml)
            call = self._client.calls.create(**kwargs)
            self._sessions[call.sid] = conference_name
            return call.sid
        else:
            stream_twiml = ""
            if self._stream_url:
                stream_twiml = f'<Start><Stream url={quoteattr(self._stream_url)} /></Start>'
            twiml = f'<Response>{stream_twiml}{self._KEEPALIVE_PAUSE}</Response>'

            kwargs: dict[str, Any] = {"to": target_number, "from_": self._from, "twiml": twiml, "record": True}
            if self._recording_status_callback:
                kwargs["recording_status_callback"] = self._recording_status_callback
                kwargs["recording_status_callback_event"] = ["completed"]

            call = self._client.calls.create(**kwargs)
            return call.sid

    # Twilio's <Pause length> caps at 60s. Chain 30 pauses (= 30 minutes) so the
    # call leg stays alive long enough for any reasonable IVR session. The
    # <Start><Stream> kicked off at dial time persists across TwiML updates and
    # keeps streaming the entire time, regardless of which Play/Say/Pause TwiML
    # is currently executing.
    _KEEPALIVE_PAUSE = '<Pause length="60"/>' * 30

    def send_dtmf(self, session_id: str, digits: str) -> None:
        """Sends DTMF tones to an in-progress call."""
        safe_digits = quoteattr(digits)
        if session_id in self._sessions:
            conf_name = self._sessions[session_id]
            twiml = f'<Response><Play digits={safe_digits}></Play><Dial><Conference>{escape(conf_name)}</Conference></Dial></Response>'
        else:
            twiml = f'<Response><Play digits={safe_digits}></Play>{self._KEEPALIVE_PAUSE}</Response>'
        self._client.calls(session_id).update(twiml=twiml)

    def play_clip(self, session_id: str, file_path: str) -> None:
        safe_path = escape(file_path)
        if session_id in self._sessions:
            conf_name = self._sessions[session_id]
            twiml = f'<Response><Play>{safe_path}</Play><Dial><Conference>{escape(conf_name)}</Conference></Dial></Response>'
        else:
            twiml = f'<Response><Play>{safe_path}</Play>{self._KEEPALIVE_PAUSE}</Response>'
        self._client.calls(session_id).update(twiml=twiml)

    def say(self, session_id: str, text: str) -> None:
        """Speaks text using Twilio TTS."""
        safe_text = escape(text)
        if session_id in self._sessions:
            conf_name = self._sessions[session_id]
            twiml = f'<Response><Say>{safe_text}</Say><Dial><Conference>{escape(conf_name)}</Conference></Dial></Response>'
        else:
            twiml = f'<Response><Say>{safe_text}</Say>{self._KEEPALIVE_PAUSE}</Response>'
        self._client.calls(session_id).update(twiml=twiml)

    def hangup(self, session_id: str) -> None:
        """Hangs up the IVR call and any associated conference legs."""
        try:
            self._client.calls(session_id).update(status="completed")
        except Exception:
            pass
        # Also terminate the user's leg if it was bridged into a conference
        if session_id in self._sessions:
            conf_name = self._sessions.pop(session_id)
            try:
                participants = self._client.conferences.list(friendly_name=conf_name, status="in-progress")
                for conf in participants:
                    for p in self._client.conferences(conf.sid).participants.list():
                        try:
                            self._client.calls(p.call_sid).update(status="completed")
                        except Exception:
                            pass
            except Exception:
                pass
