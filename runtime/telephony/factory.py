from __future__ import annotations

import os

from runtime.telephony.mock_client import MockTelephonyClient


def build_telephony():
    """
    Return a TelephonyClient based on TELEPHONY_MODE env var.

    TELEPHONY_MODE=mock   (default) — MockTelephonyClient; no network, CI-safe
    TELEPHONY_MODE=twilio           — TwilioTelephonyClient; requires Twilio creds
    """
    mode = os.getenv("TELEPHONY_MODE", "mock")

    if mode == "twilio":
        from runtime.twilio_client import TwilioTelephonyClient
        return TwilioTelephonyClient()

    return MockTelephonyClient()
