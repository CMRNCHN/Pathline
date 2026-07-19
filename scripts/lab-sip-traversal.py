#!/usr/bin/env python3
"""Place an authenticated SIP/TLS call through the complete lab IVR.

This verifier intentionally uses SIP INFO for deterministic keypad timing. The
desktop acceptance path still uses RFC 4733 RTP events.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import socket
import ssl
import sys
import time
from dataclasses import dataclass


@dataclass
class SipMessage:
    start: str
    headers: dict[str, str]
    body: bytes


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


def main() -> int:
    host = os.environ.get("LAB_SIP_SERVER", "127.0.0.1")
    port = int(os.environ.get("LAB_SIP_TLS_PORT", "5061"))
    user = os.environ.get("LAB_SIP_USER", "pathline-lab")
    password = os.environ.get("LAB_SIP_PASSWORD", "")
    if not password:
        print("LAB_SIP_PASSWORD is required", file=sys.stderr)
        return 2

    rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rtp.bind(("127.0.0.1", 0))
    rtp_port = rtp.getsockname()[1]
    conn = SipConnection(host, port)
    call_id = f"{secrets.token_hex(12)}@pathline-lab"
    from_tag = secrets.token_hex(8)
    uri = f"sip:1000@{host}"
    from_uri = f"sip:{user}@{host}"
    contact = f"<sip:{user}@{conn.local_host}:{conn.local_port};transport=tls>"
    sdp = (
        "v=0\r\n"
        f"o=pathline 1 1 IN IP4 127.0.0.1\r\ns=Pathline lab verifier\r\n"
        f"c=IN IP4 127.0.0.1\r\nt=0 0\r\nm=audio {rtp_port} RTP/AVP 0 101\r\n"
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

    challenge_name = "proxy-authenticate" if response.start.startswith("SIP/2.0 407") else "www-authenticate"
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
    for pause, digits in [(4, "1"), (6, "9"), (4, "1234#"), (4, "5678#"), (6, "1")]:
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
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"SIP traversal failed: {error}", file=sys.stderr)
        raise SystemExit(1)
