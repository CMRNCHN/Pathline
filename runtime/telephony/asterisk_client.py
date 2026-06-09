"""
Asterisk AMI telephony adapter.

Uses the Asterisk Manager Interface (AMI) for call control — no SIP stack
in Python. Asterisk handles SIP/RTP; this adapter is pure control plane.

Requires: pip install panoramisk
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import time

log = logging.getLogger(__name__)

_AMI_HOST = os.getenv("ASTERISK_AMI_HOST", "127.0.0.1")
_AMI_PORT = int(os.getenv("ASTERISK_AMI_PORT", "5038"))
_AMI_USER = os.getenv("ASTERISK_AMI_USER", "pathline")
_AMI_SECRET = os.getenv("ASTERISK_AMI_SECRET", "pathline-ami-secret")
_IVR_EXTENSION = os.getenv("ASTERISK_IVR_EXTENSION", "1000")
_IVR_CONTEXT = os.getenv("ASTERISK_IVR_CONTEXT", "ivr-test")
_SIP_CHANNEL = os.getenv("ASTERISK_SIP_CHANNEL", "PJSIP/pathline-test")


class AsteriskTelephonyClient:
    """
    TelephonyClient implementation backed by Asterisk AMI.
    Intended for local integration testing. Not for production use.
    """

    def __init__(self) -> None:
        self._active_channels: dict[str, str] = {}  # session_id -> channel name

    # ── TelephonyClient protocol ───────────────────────────────────────────────

    def dial(self, target_number: str) -> str:
        """
        Originate a call via Asterisk AMI. Returns a synthetic session ID
        (channel name) usable with send_dtmf / hangup.
        """
        channel = f"{_SIP_CHANNEL}"
        session_id = f"asterisk::{target_number}::{int(time.time())}"

        response = self._ami_action({
            "Action": "Originate",
            "Channel": channel,
            "Exten": _IVR_EXTENSION,
            "Context": _IVR_CONTEXT,
            "Priority": "1",
            "CallerID": f"Pathline <{target_number}>",
            "Timeout": "30000",
            "Variable": f"TARGET_NUMBER={target_number}",
            "Async": "true",
        })

        log.info("[ASTERISK] dial to=%s session=%s response=%s", target_number, session_id, response)
        self._active_channels[session_id] = channel
        return session_id

    def send_dtmf(self, session_id: str, digits: str) -> None:
        channel = self._active_channels.get(session_id, _SIP_CHANNEL)
        for digit in digits:
            self._ami_action({
                "Action": "PlayDTMF",
                "Channel": channel,
                "Digit": digit,
                "Duration": "500",
            })
            time.sleep(0.2)
        log.info("[ASTERISK] send_dtmf session=%s digits=%s", session_id, digits)

    def play_clip(self, session_id: str, file_path: str) -> None:
        channel = self._active_channels.get(session_id, _SIP_CHANNEL)
        self._ami_action({
            "Action": "AGI",
            "Channel": channel,
            "Command": f"STREAM FILE {file_path} \"\"",
        })
        log.info("[ASTERISK] play_clip session=%s path=%s", session_id, file_path)

    def say(self, session_id: str, text: str) -> None:
        # Asterisk AMI doesn't have a direct TTS action; log intent
        log.info("[ASTERISK] say session=%s text=%r (TTS not wired)", session_id, text)

    def hangup(self, session_id: str) -> None:
        channel = self._active_channels.pop(session_id, _SIP_CHANNEL)
        self._ami_action({
            "Action": "Hangup",
            "Channel": channel,
            "Cause": "16",
        })
        log.info("[ASTERISK] hangup session=%s", session_id)

    # ── AMI socket transport ───────────────────────────────────────────────────

    def _ami_action(self, action: dict[str, str]) -> str:
        """Send a single AMI action over a raw TCP socket. Returns raw response."""
        with socket.create_connection((_AMI_HOST, _AMI_PORT), timeout=10) as sock:
            reader = sock.makefile("rb")

            # Read banner
            reader.readline()

            # Login
            self._send(sock, {
                "Action": "Login",
                "Username": _AMI_USER,
                "Secret": _AMI_SECRET,
            })
            self._read_response(reader)

            # Send the real action
            self._send(sock, action)
            response = self._read_response(reader)

            # Logoff
            self._send(sock, {"Action": "Logoff"})

        return response

    @staticmethod
    def _send(sock: socket.socket, fields: dict[str, str]) -> None:
        msg = "".join(f"{k}: {v}\r\n" for k, v in fields.items()) + "\r\n"
        sock.sendall(msg.encode())

    @staticmethod
    def _read_response(reader) -> str:
        lines = []
        while True:
            raw = reader.readline()
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if not line:
                break
            lines.append(line)
        return "\n".join(lines)
