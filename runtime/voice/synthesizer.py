from __future__ import annotations

import structlog

log = structlog.get_logger()


class VoiceSynthesizer:
    """Injects synthesized speech into a live Twilio call via TwiML <Say>."""

    def __init__(self, telephony_client) -> None:
        self._client = telephony_client

    async def inject_into_call(self, call_sid: str, text: str) -> None:
        log.info("voice_inject", call_sid=call_sid, text=text[:80])
        self._client.say(call_sid, text)
