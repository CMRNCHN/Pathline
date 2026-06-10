from __future__ import annotations

import os

from runtime.telephony.mock_client import MockTelephonyClient


def build_telephony():
    """
    Return a TelephonyClient based on TELEPHONY_MODE env var.

    TELEPHONY_MODE=mock      (default) — MockTelephonyClient; no network, CI-safe
    TELEPHONY_MODE=asterisk            — AsteriskTelephonyClient; local PBX via AMI
    TELEPHONY_MODE=twilio              — TwilioTelephonyClient; requires Twilio creds
    """
    mode = os.getenv("TELEPHONY_MODE", "mock")

    if mode == "asterisk":
        from runtime.telephony.asterisk_client import AsteriskTelephonyClient
        return AsteriskTelephonyClient()

    if mode == "twilio":
        from runtime.telephony.twilio_client import TwilioTelephonyClient
        return TwilioTelephonyClient()

    return MockTelephonyClient()
