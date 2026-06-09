"""runtime/telephony/twilio_client.py — Twilio outbound call management.

Handles:
  - Placing outbound calls with Media Streams TwiML
  - Hanging up calls
  - Injecting DTMF tones mid-call
  - Receiving Twilio Media Stream WebSocket frames → audio queue

Requirements:
    pip install twilio>=8.0.0
    Environment: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_CALLER_ID

The WebSocket handler (handle_media_stream) is the integration point between
Twilio's real-time audio and the DeepgramStreamClient.

Twilio sends mulaw-encoded audio at 8kHz in base64-encoded JSON frames.
This module decodes them and pushes raw mulaw bytes into an asyncio.Queue
for the STT client to consume.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CallRecord:
    """Minimal record of an active call."""
    call_sid: str
    to_number: str
    from_number: str
    status: str = 'initiated'


class TwilioClient:
    """Manage outbound IVR calls and real-time audio streaming.

    Args:
        account_sid: Twilio account SID.
        auth_token: Twilio auth token.
        caller_id: The phone number to call from (must be a Twilio number).
        stream_host: Public host where Twilio will send the Media Stream
                     WebSocket (e.g. 'yourserver.ngrok.io').
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        caller_id: str,
        stream_host: str,
    ) -> None:
        try:
            import twilio.rest  # noqa: F401 — availability check
        except ImportError as e:
            raise RuntimeError("twilio is required: pip install twilio>=8.0.0") from e

        self._client = __import__('twilio').rest.Client(account_sid, auth_token)
        self._caller_id = caller_id
        self._stream_host = stream_host

    # ── Call lifecycle ──────────────────────────────────────────────────────

    def place_call(
        self,
        to: str,
        session_id: str,
        status_callback: str | None = None,
    ) -> CallRecord:
        """Place an outbound call and set up Media Streams.

        Args:
            to: The IVR phone number to call.
            session_id: Used to correlate the stream WebSocket with the session.
            status_callback: URL for Twilio to POST call status updates to.

        Returns:
            CallRecord with the call SID.
        """
        stream_url = f'wss://{self._stream_host}/media-stream/{session_id}'
        twiml = self._stream_twiml(stream_url)

        logger.info('Placing call to %s for session %s', to, session_id)

        call = self._client.calls.create(
            to=to,
            from_=self._caller_id,
            twiml=twiml,
            **(({'status_callback': status_callback,
                 'status_callback_method': 'POST',
                 'status_callback_event': ['initiated', 'ringing', 'answered', 'completed']})
               if status_callback else {}),
        )

        logger.info('Call placed: SID=%s', call.sid)
        return CallRecord(
            call_sid=call.sid,
            to_number=to,
            from_number=self._caller_id,
            status=call.status,
        )

    def hangup(self, call_sid: str) -> None:
        """Hang up an active call immediately."""
        logger.info('Hanging up call %s', call_sid)
        try:
            self._client.calls(call_sid).update(status='completed')
        except Exception as e:
            logger.error('Hangup failed for %s: %s', call_sid, e)

    def inject_dtmf(self, call_sid: str, digits: str) -> None:
        """Inject DTMF tones into an active call.

        Args:
            call_sid: The SID of the active call.
            digits: DTMF digit(s) to send (e.g. '1', '##', '1234').
        """
        logger.info('Injecting DTMF "%s" into call %s', digits, call_sid)
        # Escape digits for TwiML
        safe_digits = digits.replace('&', '&amp;').replace('<', '&lt;')
        self._client.calls(call_sid).update(
            twiml=f'<Response><Play digits="{safe_digits}"/><Pause length="30"/></Response>'
        )

    # ── Media stream WebSocket handler ──────────────────────────────────────

    async def handle_media_stream(
        self,
        websocket: Any,
        audio_queue: asyncio.Queue,
    ) -> None:
        """Process Twilio Media Stream WebSocket frames into audio_queue.

        Call this in a task alongside DeepgramStreamClient.stream().
        When the WebSocket closes, pushes None sentinel to audio_queue.

        Twilio frame format:
          {"event": "media", "media": {"payload": "<base64 mulaw audio>"}}
          {"event": "stop", ...}

        Args:
            websocket: The WebSocket connection from Twilio.
            audio_queue: Queue to push raw mulaw audio bytes into.
        """
        try:
            async for raw_message in websocket:
                try:
                    msg = json.loads(raw_message)
                except (json.JSONDecodeError, TypeError):
                    continue

                event = msg.get('event', '')

                if event == 'media':
                    payload = msg.get('media', {}).get('payload', '')
                    if payload:
                        audio_bytes = base64.b64decode(payload)
                        await audio_queue.put(audio_bytes)

                elif event == 'stop':
                    logger.info('Twilio Media Stream stopped')
                    break

                elif event == 'connected':
                    logger.info('Twilio Media Stream connected')

        except Exception as e:
            logger.error('Media stream error: %s', e)
        finally:
            await audio_queue.put(None)  # sentinel — signals Deepgram to stop

    # ── TwiML helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _stream_twiml(stream_url: str) -> str:
        """Generate TwiML that connects a call to a Media Stream."""
        return (
            '<Response>'
            '<Connect>'
            f'<Stream url="{stream_url}" track="inbound_track"/>'
            '</Connect>'
            '</Response>'
        )


def client_from_env(stream_host: str) -> TwilioClient:
    """Construct a TwilioClient from environment variables.

    Required env vars:
        TWILIO_ACCOUNT_SID
        TWILIO_AUTH_TOKEN
        TWILIO_CALLER_ID
    """
    return TwilioClient(
        account_sid=os.environ['TWILIO_ACCOUNT_SID'],
        auth_token=os.environ['TWILIO_AUTH_TOKEN'],
        caller_id=os.environ['TWILIO_CALLER_ID'],
        stream_host=stream_host,
    )
