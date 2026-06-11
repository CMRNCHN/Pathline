"""
Asterisk AMI telephony adapter.

Uses the Asterisk Manager Interface (AMI) for call control — no SIP stack
in Python. Asterisk handles SIP/RTP; this adapter is pure control plane.

Originate uses a Local channel (Local/1000@ivr-test/n) so no registered
SIP endpoint is required. One leg runs the IVR dialplan; the other is the
"caller" leg we send DTMF to.
"""
from __future__ import annotations

import logging
import os
import socket
import time
import uuid

log = logging.getLogger(__name__)

_AMI_HOST   = os.getenv("ASTERISK_AMI_HOST",   "127.0.0.1")
_AMI_PORT   = int(os.getenv("ASTERISK_AMI_PORT",   "5038"))
_AMI_USER   = os.getenv("ASTERISK_AMI_USER",   "pathline")
_AMI_SECRET = os.getenv("ASTERISK_AMI_SECRET", "pathline-ami-secret")
_IVR_EXT    = os.getenv("ASTERISK_IVR_EXTENSION", "1000")
_IVR_CTX    = os.getenv("ASTERISK_IVR_CONTEXT",   "ivr-test")


class AsteriskTelephonyClient:
    """
    TelephonyClient implementation backed by Asterisk AMI.
    Intended for local integration testing. Not for production use.
    """

    def __init__(self) -> None:
        # session_id -> (ivr_channel, caller_channel)
        self._sessions: dict[str, tuple[str, str]] = {}

    # ── TelephonyClient protocol ───────────────────────────────────────────────

    def dial(self, target_number: str) -> str:
        """
        Originate a Local channel call into the IVR dialplan.
        Returns a session_id usable with send_dtmf / hangup.

        Local/1000@ivr-test/n creates two legs (no SIP registration needed):
          ;2 = IVR leg  — runs the dialplan (Playback / WaitExten / etc.)
          ;1 = caller leg — DTMF sent here propagates into ;2's dialplan
        """
        action_id = uuid.uuid4().hex[:12]
        # /n flag keeps both legs alive independently so PlayDTMF works
        channel = f"Local/{_IVR_EXT}@{_IVR_CTX}/n"

        with self._session() as (sock, reader):
            self._send(sock, {
                "Action":    "Originate",
                "ActionID":  action_id,
                "Channel":   channel,
                "Application": "Wait",
                "Data":      "30",
                "CallerID":  f"Pathline <{target_number}>",
                "Async":     "true",
            })
            # Read immediate Queued response (discard — just drains the buffer)
            self._read_response(reader)
            # Read OriginateResponse event to get actual channel name
            channel_name = self._wait_for_originate(reader, action_id)

        session_id = f"asterisk::{target_number}::{action_id}"
        ivr_ch  = f"{channel_name};2"   # runs dialplan (Playback / WaitExten)
        call_ch = f"{channel_name};1"   # receives DTMF injection → propagates into ;2
        self._sessions[session_id] = (ivr_ch, call_ch)

        log.info("[ASTERISK] dial to=%s channel=%s session=%s", target_number, channel_name, session_id)
        return session_id

    def send_dtmf(self, session_id: str, digits: str) -> None:
        _, call_ch = self._sessions.get(session_id, ("", ""))
        if not call_ch:
            log.warning("[ASTERISK] send_dtmf: unknown session %s", session_id)
            return
        for digit in digits:
            self._ami_action({
                "Action":   "PlayDTMF",
                "Channel":  call_ch,
                "Digit":    digit,
                "Duration": "500",
            })
            time.sleep(0.15)
        log.info("[ASTERISK] send_dtmf session=%s digits=%s", session_id, digits)

    def play_clip(self, session_id: str, file_path: str) -> None:
        ivr_ch, _ = self._sessions.get(session_id, ("", ""))
        if ivr_ch:
            self._ami_action({"Action": "AGI", "Channel": ivr_ch,
                              "Command": f'STREAM FILE {file_path} ""'})
        log.info("[ASTERISK] play_clip session=%s path=%s", session_id, file_path)

    def say(self, session_id: str, text: str) -> None:
        log.info("[ASTERISK] say session=%s text=%r (TTS not wired)", session_id, text)

    def hangup(self, session_id: str) -> None:
        channels = self._sessions.pop(session_id, ("", ""))
        for ch in channels:
            if ch:
                try:
                    self._ami_action({"Action": "Hangup", "Channel": ch, "Cause": "16"})
                except Exception:
                    pass  # channel may already be gone
        log.info("[ASTERISK] hangup session=%s", session_id)

    # ── AMI transport ─────────────────────────────────────────────────────────

    def _ami_action(self, action: dict[str, str]) -> str:
        with self._session() as (sock, reader):
            self._send(sock, action)
            return self._read_response(reader)

    class _session:
        """Context manager: open AMI socket, login, yield (sock, reader), logoff."""
        def __init__(self):
            self._sock = None
            self._reader = None

        def __enter__(self):
            self._sock = socket.create_connection((_AMI_HOST, _AMI_PORT), timeout=10)
            self._reader = self._sock.makefile("rb")
            self._reader.readline()  # banner
            AsteriskTelephonyClient._send(self._sock, {
                "Action":   "Login",
                "Username": _AMI_USER,
                "Secret":   _AMI_SECRET,
            })
            AsteriskTelephonyClient._read_response(self._reader)
            return self._sock, self._reader

        def __exit__(self, *_):
            try:
                AsteriskTelephonyClient._send(self._sock, {"Action": "Logoff"})
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass

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

    @staticmethod
    def _wait_for_originate(reader, action_id: str, timeout: float = 10.0) -> str:
        """
        Read AMI event stream until OriginateResponse matching action_id.
        Returns the channel name from the event.
        """
        deadline = time.monotonic() + timeout
        event_lines: list[str] = []

        while time.monotonic() < deadline:
            raw = reader.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")

            if line:
                event_lines.append(line)
            else:
                # blank line = end of event block
                block = {k.strip(): v.strip()
                         for k, v in (ln.split(":", 1) for ln in event_lines if ":" in ln)}
                event_lines = []

                if (block.get("Event") == "OriginateResponse"
                        and block.get("ActionID") == action_id):
                    ch = block.get("Channel", "")
                    # Strip ;1 or ;2 suffix to get the base channel name
                    return ch.rstrip(";12").rstrip(";").rsplit(";", 1)[0] if ";" in ch else ch

        raise TimeoutError(f"OriginateResponse for {action_id} not received within {timeout}s")
