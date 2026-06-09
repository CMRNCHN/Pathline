from __future__ import annotations

import logging
import uuid

log = logging.getLogger(__name__)


class MockTelephonyClient:
    """No-op telephony client. Safe for CI, testing, and dry-run contexts."""

    def dial(self, target_number: str) -> str:
        sid = f"mock-call-{uuid.uuid4().hex[:12]}"
        log.info("[MOCK] dial to=%s sid=%s", target_number, sid)
        return sid

    def send_dtmf(self, session_id: str, digits: str) -> None:
        log.info("[MOCK] send_dtmf session=%s digits=%s", session_id, digits)

    def play_clip(self, session_id: str, file_path: str) -> None:
        log.info("[MOCK] play_clip session=%s path=%s", session_id, file_path)

    def say(self, session_id: str, text: str) -> None:
        log.info("[MOCK] say session=%s text=%r", session_id, text)

    def hangup(self, session_id: str) -> None:
        log.info("[MOCK] hangup session=%s", session_id)
