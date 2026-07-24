#!/usr/bin/env python3
"""Place an authenticated SIP/TLS call through the complete lab IVR.

Optionally records inbound RTP (PCMU) to a WAV + DTMF timeline JSON for
future STT/fixture reuse when PATHLINE_LAB_RECORD=1 (or --record).

This verifier intentionally uses SIP INFO for deterministic keypad timing. The
desktop acceptance path still uses RFC 4733 RTP events.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import socket
import ssl
import struct
import sys
import threading
import time
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# ITU-T G.711 µ-law → linear PCM16
def _build_ulaw_table() -> tuple[int, ...]:
    table = []
    for i in range(256):
        u = (~i) & 0xFF
        sign = u & 0x80
        exponent = (u >> 4) & 0x07
        mantissa = u & 0x0F
        sample = ((mantissa << 3) + 0x84) << exponent
        sample -= 0x84
        table.append(-sample if sign else sample)
    return tuple(table)


_ULAW_DECODE = _build_ulaw_table()


def ulaw_bytes_to_pcm16(payload: bytes) -> bytes:
    return b"".join(struct.pack("<h", _ULAW_DECODE[b]) for b in payload)


@dataclass
class SipMessage:
    start: str
    headers: dict[str, str]
    body: bytes


@dataclass
class CallRecorder:
    """Capture inbound PCMU RTP and DTMF events for lab reuse."""

    out_dir: Path
    sample_rate: int = 8000
    started_at: float = field(default_factory=time.monotonic)
    pcm_chunks: list[bytes] = field(default_factory=list)
    dtmf_events: list[dict] = field(default_factory=list)
    rtp_packets: int = 0
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None

    def start(self, rtp_sock: socket.socket) -> None:
        self.thread = threading.Thread(
            target=self._capture_loop, args=(rtp_sock,), name="lab-rtp-record", daemon=True
        )
        self.thread.start()

    def note_dtmf(self, digits: str) -> None:
        self.dtmf_events.append(
            {
                "t_ms": int((time.monotonic() - self.started_at) * 1000),
                "digits": digits,
                # Privacy: also store non-reversible short hash for ledger-style audits.
                "hash": hashlib.sha256(digits.encode()).hexdigest()[:16],
            }
        )

    def stop_and_write(self, meta: dict) -> tuple[Path, Path]:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)

        self.out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        wav_path = self.out_dir / f"lab-call-{stamp}.wav"
        json_path = self.out_dir / f"lab-call-{stamp}.json"

        pcm = b"".join(self.pcm_chunks)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm)

        duration_s = len(pcm) / (2 * self.sample_rate) if pcm else 0.0
        payload = {
            **meta,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "wav": wav_path.name,
            "sample_rate": self.sample_rate,
            "channels": 1,
            "encoding": "pcm_s16le",
            "duration_seconds": round(duration_s, 3),
            "rtp_packets": self.rtp_packets,
            "bytes": len(pcm),
            "dtmf": self.dtmf_events,
            "dtmf_sequence": "".join(e["digits"] for e in self.dtmf_events),
            "purpose": "lab live-call capture for STT/DTMF fixture reuse",
        }
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return wav_path, json_path

    def _capture_loop(self, rtp_sock: socket.socket) -> None:
        rtp_sock.settimeout(0.25)
        while not self.stop_event.is_set():
            try:
                packet, _ = rtp_sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break
            if len(packet) < 12:
                continue
            # RTP header: V=2, PT in low 7 bits of byte 1
            pt = packet[1] & 0x7F
            if pt != 0:  # PCMU only
                continue
            payload = packet[12:]
            if not payload:
                continue
            self.pcm_chunks.append(ulaw_bytes_to_pcm16(payload))
            self.rtp_packets += 1


class SipConnection:
    def __init__(self, host: str, port: int) -> None:
        raw = socket.create_connection((host, port), timeout=10)
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.sock = context.wrap_socket(raw, server_hostname=host)
        self.sock.settimeout(20)
        self.local_host, self.local_port = self.sock.getsockname()[:2]
        self.reader = self.sock.makefile("rb")

    def send(self, start: str, headers: list[tuple[str, str]], body: bytes = b"") -> None:
        fields = headers + [("Content-Length", str(len(body)))]
        wire = start + "\r\n" + "".join(f"{key}: {value}\r\n" for key, value in fields)
        self.sock.sendall(wire.encode("utf-8") + b"\r\n" + body)

    def receive(self) -> SipMessage:
        start = self.reader.readline().decode("utf-8").strip()
        if not start:
            raise RuntimeError("SIP connection closed")
        headers: dict[str, str] = {}
        while True:
            line = self.reader.readline().decode("utf-8").strip()
            if not line:
                break
            key, value = line.split(":", 1)
            headers[key.lower()] = value.strip()
        body = self.reader.read(int(headers.get("content-length", "0")))
        return SipMessage(start, headers, body)


def md5_hex(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def digest_header(challenge: str, user: str, password: str, method: str, uri: str) -> str:
    values = {
        key.lower(): quoted or bare
        for key, quoted, bare in re.findall(r'(\w+)=(?:"([^"]*)"|([^,\s]+))', challenge)
    }
    realm = values["realm"]
    nonce = values["nonce"]
    qop = "auth" if "auth" in values.get("qop", "") else ""
    nc = "00000001"
    cnonce = secrets.token_hex(8)
    ha1 = md5_hex(f"{user}:{realm}:{password}")
    ha2 = md5_hex(f"{method}:{uri}")
    response = (
        md5_hex(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
        if qop
        else md5_hex(f"{ha1}:{nonce}:{ha2}")
    )
    parts = [
        f'username="{user}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{uri}"',
        f'response="{response}"',
        "algorithm=MD5",
    ]
    if qop:
        parts.extend([f"qop={qop}", f"nc={nc}", f'cnonce="{cnonce}"'])
    if "opaque" in values:
        parts.append(f'opaque="{values["opaque"]}"')
    return "Digest " + ", ".join(parts)


def pick_rtp_port(start: int = 10000, end: int = 10100) -> tuple[socket.socket, int]:
    """Bind UDP in the Docker-published RTP range so Asterisk media can reach us."""
    for port in range(start, end + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("0.0.0.0", port))
            return sock, port
        except OSError:
            sock.close()
    raise RuntimeError(f"no free RTP port in {start}-{end}")


def advertise_rtp_ip() -> str:
    """IP Asterisk-in-Docker should send RTP to (not the host's loopback/VPN view)."""
    override = os.environ.get("LAB_RTP_ADVERTISE_IP", "").strip()
    if override:
        return override

    # Prefer the address the Asterisk container itself resolves for the host.
    try:
        import subprocess

        out = subprocess.check_output(
            [
                "docker",
                "compose",
                "--profile",
                "lab",
                "exec",
                "-T",
                "asterisk",
                "getent",
                "hosts",
                "host.docker.internal",
            ],
            cwd=str(Path(__file__).resolve().parents[1]),
            text=True,
            timeout=5,
        )
        ip = out.split()[0].strip()
        if ip and not ip.startswith("127."):
            return ip
    except (OSError, subprocess.SubprocessError, IndexError):
        pass

    # Colima / Docker Desktop common host gateways (container → Mac).
    for candidate in ("192.168.5.2", "192.168.65.2"):
        return candidate

    for host in ("host.docker.internal", "host.lima.internal"):
        try:
            ip = socket.gethostbyname(host)
            if not ip.startswith("127."):
                return ip
        except OSError:
            continue
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    finally:
        probe.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record",
        action="store_true",
        default=os.environ.get("PATHLINE_LAB_RECORD", "").lower() in {"1", "true", "yes"},
        help="Write inbound RTP WAV + DTMF JSON under lab/recordings/",
    )
    parser.add_argument(
        "--out-dir",
        default=os.environ.get(
            "PATHLINE_LAB_RECORD_DIR",
            str(Path(__file__).resolve().parents[1] / "lab" / "recordings"),
        ),
        help="Directory for recording artifacts",
    )
    args = parser.parse_args()

    host = os.environ.get("LAB_SIP_SERVER", "127.0.0.1")
    port = int(os.environ.get("LAB_SIP_TLS_PORT", "5061"))
    user = os.environ.get("LAB_SIP_USER", "pathline-lab")
    password = os.environ.get("LAB_SIP_PASSWORD", "")
    if not password:
        print("LAB_SIP_PASSWORD is required", file=sys.stderr)
        return 2

    rtp, rtp_port = pick_rtp_port()
    rtp_ip = advertise_rtp_ip()
    recorder = CallRecorder(out_dir=Path(args.out_dir)) if args.record else None
    if recorder:
        recorder.start(rtp)
        print(f"Recording RTP on {rtp_ip}:{rtp_port} (advertised to Asterisk)")

    conn = SipConnection(host, port)
    call_id = f"{secrets.token_hex(12)}@pathline-lab"
    from_tag = secrets.token_hex(8)
    uri = f"sip:1000@{host}"
    from_uri = f"sip:{user}@{host}"
    contact = f"<sip:{user}@{conn.local_host}:{conn.local_port};transport=tls>"
    sdp = (
        "v=0\r\n"
        f"o=pathline 1 1 IN IP4 {rtp_ip}\r\ns=Pathline lab verifier\r\n"
        f"c=IN IP4 {rtp_ip}\r\nt=0 0\r\nm=audio {rtp_port} RTP/AVP 0 101\r\n"
        "a=rtpmap:0 PCMU/8000\r\na=rtpmap:101 telephone-event/8000\r\n"
        "a=fmtp:101 0-16\r\na=recvonly\r\n"
    ).encode()

    def base_headers(branch: str, cseq: int, method: str) -> list[tuple[str, str]]:
        return [
            ("Via", f"SIP/2.0/TLS {conn.local_host}:{conn.local_port};branch={branch};rport"),
            ("Max-Forwards", "70"),
            ("From", f"<{from_uri}>;tag={from_tag}"),
            ("To", f"<{uri}>"),
            ("Call-ID", call_id),
            ("CSeq", f"{cseq} {method}"),
            ("Contact", contact),
            ("User-Agent", "Pathline-Lab-Verifier/1"),
        ]

    try:
        branch = f"z9hG4bK{secrets.token_hex(8)}"
        invite_headers = base_headers(branch, 1, "INVITE") + [("Content-Type", "application/sdp")]
        conn.send(f"INVITE {uri} SIP/2.0", invite_headers, sdp)
        response = conn.receive()
        while response.start.startswith("SIP/2.0 1"):
            response = conn.receive()
        if not response.start.startswith(("SIP/2.0 401", "SIP/2.0 407")):
            raise RuntimeError(f"expected SIP auth challenge, got {response.start}")

        to_value = response.headers["to"]
        ack_headers = base_headers(branch, 1, "ACK")
        ack_headers[3] = ("To", to_value)
        conn.send(f"ACK {uri} SIP/2.0", ack_headers)

        challenge_name = (
            "proxy-authenticate" if response.start.startswith("SIP/2.0 407") else "www-authenticate"
        )
        auth_name = "Proxy-Authorization" if challenge_name == "proxy-authenticate" else "Authorization"
        branch = f"z9hG4bK{secrets.token_hex(8)}"
        invite_headers = base_headers(branch, 2, "INVITE") + [
            (auth_name, digest_header(response.headers[challenge_name], user, password, "INVITE", uri)),
            ("Content-Type", "application/sdp"),
        ]
        conn.send(f"INVITE {uri} SIP/2.0", invite_headers, sdp)
        response = conn.receive()
        while response.start.startswith("SIP/2.0 1"):
            response = conn.receive()
        if not response.start.startswith("SIP/2.0 200"):
            raise RuntimeError(f"authenticated INVITE failed: {response.start}")
        dialog_to = response.headers["to"]
        remote_contact = response.headers.get("contact", f"<{uri}>")
        contact_match = re.search(r"<([^>]+)>", remote_contact)
        request_uri = contact_match.group(1) if contact_match else uri

        ack_headers = base_headers(f"z9hG4bK{secrets.token_hex(8)}", 2, "ACK")
        ack_headers[3] = ("To", dialog_to)
        conn.send(f"ACK {request_uri} SIP/2.0", ack_headers)

        cseq = 3
        # Sound files are often missing in the container image, so prompts collapse
        # to short SayPhonetic clips. Keep pauses under WaitExten(10).
        for pause, digits in [(8, "1"), (10, "9"), (6, "1234#"), (6, "5678#"), (8, "1")]:
            time.sleep(pause)
            for digit in digits:
                info_headers = base_headers(f"z9hG4bK{secrets.token_hex(8)}", cseq, "INFO")
                info_headers[3] = ("To", dialog_to)
                info_headers.append(("Content-Type", "application/dtmf-relay"))
                conn.send(
                    f"INFO {request_uri} SIP/2.0",
                    info_headers,
                    f"Signal={digit}\r\nDuration=160\r\n".encode(),
                )
                info_response = conn.receive()
                while info_response.start.startswith("SIP/2.0 1"):
                    info_response = conn.receive()
                if info_response.start.startswith("BYE "):
                    raise RuntimeError(
                        f"remote BYE before DTMF {digit!r}; check dialplan timing/DTMF mode"
                    )
                if not info_response.start.startswith("SIP/2.0 200"):
                    raise RuntimeError(f"DTMF INFO {digit!r} failed: {info_response.start}")
                if recorder:
                    recorder.note_dtmf(digit)
                cseq += 1
                time.sleep(0.25)

        conn.sock.settimeout(45)
        message = conn.receive()
        if not message.start.startswith("BYE "):
            raise RuntimeError(f"expected remote BYE after IVR traversal, got {message.start}")
        response_headers = [
            ("Via", message.headers["via"]),
            ("From", message.headers["from"]),
            ("To", message.headers["to"]),
            ("Call-ID", message.headers["call-id"]),
            ("CSeq", message.headers["cseq"]),
        ]
        conn.send("SIP/2.0 200 OK", response_headers)
        print("SIP/TLS traversal passed: 1000 -> menus -> remote BYE")

        if recorder:
            wav_path, json_path = recorder.stop_and_write(
                {
                    "call_id": call_id,
                    "target": "1000",
                    "sip_server": f"{host}:{port}",
                    "transport": "tls",
                    "dtmf_mode": "SIP INFO",
                    "path": "lab-account-status",
                    "rtp_advertise": f"{rtp_ip}:{rtp_port}",
                }
            )
            print(f"Recording saved: {wav_path}")
            print(f"Metadata saved:  {json_path}")
            if wav_path.stat().st_size < 1000:
                print(
                    "warning: WAV is very small — Asterisk may not have sent much RTP "
                    "(missing sound prompts often yield short SayPhonetic clips).",
                    file=sys.stderr,
                )
        return 0
    finally:
        if recorder and recorder.thread and recorder.thread.is_alive():
            recorder.stop_event.set()
            recorder.thread.join(timeout=2)
        try:
            rtp.close()
        except OSError:
            pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"SIP traversal failed: {error}", file=sys.stderr)
        raise SystemExit(1)
