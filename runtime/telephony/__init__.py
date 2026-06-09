"""
Telephony subsystem.

Canonical entry point: build_telephony()

Direct TwilioTelephonyClient construction is reserved for:
- CLI tools with explicit user-provided credentials
- Test harnesses that need a real adapter
- Explicit credential injection flows (e.g. analyst GUI dial form)

All other callers must use build_telephony().
"""
from __future__ import annotations

from typing import Protocol

from runtime.telephony.factory import build_telephony as build_telephony

__all__ = ["build_telephony", "TelephonyClient"]


class TelephonyClient(Protocol):
    def dial(self, target_number: str) -> str: ...
    def send_dtmf(self, session_id: str, digits: str) -> None: ...
    def play_clip(self, session_id: str, file_path: str) -> None: ...
    def say(self, session_id: str, text: str) -> None: ...
    def hangup(self, session_id: str) -> None: ...
