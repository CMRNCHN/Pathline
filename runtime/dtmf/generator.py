from __future__ import annotations

import structlog

log = structlog.get_logger()


class DTMFGenerator:
    """Sends DTMF digits into a live Twilio call."""

    def __init__(self, twilio_client) -> None:
        self._client = twilio_client

    async def inject_into_call(self, call_sid: str, digits: str) -> None:
        log.info("dtmf_inject", call_sid=call_sid, digits=digits)
        self._client.send_dtmf(call_sid, digits)
