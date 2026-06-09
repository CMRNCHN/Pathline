"""
Integration tests for the Asterisk local IVR stack.

Requires TELEPHONY_MODE=asterisk and a running Asterisk container:

    cd infrastructure && docker compose up asterisk -d
    TELEPHONY_MODE=asterisk pytest tests/test_asterisk_ivr.py -v

These tests are skipped automatically when Asterisk is not reachable,
so they do not break CI runs that have no local PBX.
"""
from __future__ import annotations

import os
import socket
import time

import pytest

_AMI_HOST = os.getenv("ASTERISK_AMI_HOST", "127.0.0.1")
_AMI_PORT = int(os.getenv("ASTERISK_AMI_PORT", "5038"))


def _asterisk_reachable() -> bool:
    try:
        with socket.create_connection((_AMI_HOST, _AMI_PORT), timeout=2):
            return True
    except OSError:
        return False


asterisk_only = pytest.mark.skipif(
    not _asterisk_reachable(),
    reason="Asterisk AMI not reachable — start the container first",
)


# ── Factory / import tests (always run) ───────────────────────────────────────

def test_factory_mock_default():
    """build_telephony() returns MockTelephonyClient when TELEPHONY_MODE unset."""
    os.environ.pop("TELEPHONY_MODE", None)
    from runtime.telephony import build_telephony
    from runtime.telephony.mock_client import MockTelephonyClient
    client = build_telephony()
    assert isinstance(client, MockTelephonyClient)


def test_factory_asterisk_mode(monkeypatch):
    """build_telephony() returns AsteriskTelephonyClient when mode=asterisk."""
    monkeypatch.setenv("TELEPHONY_MODE", "asterisk")
    from runtime.telephony.factory import build_telephony
    from runtime.telephony.asterisk_client import AsteriskTelephonyClient
    client = build_telephony()
    assert isinstance(client, AsteriskTelephonyClient)


def test_mock_sid_deterministic():
    """Mock dial returns stable SID for same input."""
    from runtime.telephony.mock_client import MockTelephonyClient
    c = MockTelephonyClient()
    assert c.dial("+15550001234") == c.dial("+15550001234")


def test_mock_protocol_complete():
    """MockTelephonyClient implements all five protocol methods without error."""
    from runtime.telephony.mock_client import MockTelephonyClient
    c = MockTelephonyClient()
    sid = c.dial("+15550001234")
    c.send_dtmf(sid, "1")
    c.play_clip(sid, "/tmp/test.wav")
    c.say(sid, "hello")
    c.hangup(sid)


# ── Live Asterisk IVR tests (skipped when container not running) ───────────────

@asterisk_only
def test_ami_reachable():
    """AMI socket accepts connections."""
    assert _asterisk_reachable()


@asterisk_only
def test_dial_returns_session_id():
    """dial() returns a non-empty session ID."""
    from runtime.telephony.asterisk_client import AsteriskTelephonyClient
    client = AsteriskTelephonyClient()
    sid = client.dial("+15550001000")
    assert sid.startswith("asterisk::")
    client.hangup(sid)


@asterisk_only
def test_dtmf_digit_1_status():
    """Press 1 → IVR responds with status path (no exception)."""
    from runtime.telephony.asterisk_client import AsteriskTelephonyClient
    client = AsteriskTelephonyClient()
    sid = client.dial("+15550001000")
    time.sleep(2)          # wait for IVR to answer and play menu
    client.send_dtmf(sid, "1")
    time.sleep(1)
    client.hangup(sid)


@asterisk_only
def test_dtmf_digit_9_hangup():
    """Press 9 → clean hangup, no exception."""
    from runtime.telephony.asterisk_client import AsteriskTelephonyClient
    client = AsteriskTelephonyClient()
    sid = client.dial("+15550001000")
    time.sleep(2)
    client.send_dtmf(sid, "9")
    time.sleep(1)
    # hangup after IVR has already ended is graceful
    client.hangup(sid)


@asterisk_only
def test_dtmf_invalid_then_reprompt():
    """Invalid digit causes reprompt; second invalid causes hangup."""
    from runtime.telephony.asterisk_client import AsteriskTelephonyClient
    client = AsteriskTelephonyClient()
    sid = client.dial("+15550001000")
    time.sleep(2)
    client.send_dtmf(sid, "5")   # invalid — reprompt
    time.sleep(2)
    client.send_dtmf(sid, "5")   # invalid again — IVR hangs up
    time.sleep(1)
    client.hangup(sid)            # graceful even if already hung up
