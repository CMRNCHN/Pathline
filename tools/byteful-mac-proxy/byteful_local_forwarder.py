#!/usr/bin/env python3
"""Local HTTP proxy that adds Byteful credentials so macOS needs no Keychain auth."""

from __future__ import annotations

import argparse
import base64
import select
import socket
import socketserver
import sys

DEFAULT_LISTEN = ("127.0.0.1", 8118)
DEFAULT_UPSTREAM = ("residential.byteful.com", 8166)


class Handler(socketserver.BaseRequestHandler):
    upstream_host = DEFAULT_UPSTREAM[0]
    upstream_port = DEFAULT_UPSTREAM[1]
    auth_header = ""

    def handle(self) -> None:
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = self.request.recv(4096)
            if not chunk:
                return
            header += chunk
        head, _, leftover = header.partition(b"\r\n\r\n")
        first = head.split(b"\r\n", 1)[0].decode("iso-8859-1", "replace")
        parts = first.split(" ")
        if len(parts) < 2 or parts[0].upper() != "CONNECT":
            self.request.sendall(b"HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n")
            return
        target = parts[1]
        try:
            upstream = socket.create_connection((self.upstream_host, self.upstream_port), timeout=20)
        except OSError:
            self.request.sendall(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            return
        connect = (
            f"CONNECT {target} HTTP/1.1\r\n"
            f"Host: {target}\r\n"
            f"Proxy-Authorization: Basic {self.auth_header}\r\n"
            f"Proxy-Connection: keep-alive\r\n\r\n"
        ).encode("ascii")
        upstream.sendall(connect)
        reply = b""
        while b"\r\n\r\n" not in reply:
            chunk = upstream.recv(4096)
            if not chunk:
                upstream.close()
                return
            reply += chunk
        status_line = reply.split(b"\r\n", 1)[0]
        if b" 200 " not in status_line:
            self.request.sendall(b"HTTP/1.1 407 Proxy Authentication Required\r\nConnection: close\r\n\r\n")
            upstream.close()
            return
        self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        extra = reply.split(b"\r\n\r\n", 1)[1]
        if extra:
            self.request.sendall(extra)
        if leftover:
            upstream.sendall(leftover)
        pipe(self.request, upstream)


class ThreadedServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def pipe(left: socket.socket, right: socket.socket) -> None:
    sockets = [left, right]
    try:
        while True:
            readable, _, _ = select.select(sockets, [], [], 60)
            if not readable:
                return
            for sock in readable:
                other = right if sock is left else left
                data = sock.recv(65536)
                if not data:
                    return
                other.sendall(data)
    except OSError:
        return
    finally:
        try:
            left.close()
        except OSError:
            pass
        try:
            right.close()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Forward 127.0.0.1 to Byteful with Basic auth.")
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--upstream-host", default=DEFAULT_UPSTREAM[0])
    parser.add_argument("--upstream-port", type=int, default=DEFAULT_UPSTREAM[1])
    parser.add_argument("--listen-host", default=DEFAULT_LISTEN[0])
    parser.add_argument("--listen-port", type=int, default=DEFAULT_LISTEN[1])
    args = parser.parse_args(argv)
    Handler.upstream_host = args.upstream_host
    Handler.upstream_port = args.upstream_port
    Handler.auth_header = base64.b64encode(f"{args.user}:{args.password}".encode()).decode("ascii")
    server = ThreadedServer((args.listen_host, args.listen_port), Handler)
    print(
        f"Byteful local forwarder on {args.listen_host}:{args.listen_port} -> "
        f"{args.upstream_host}:{args.upstream_port}",
        flush=True,
    )
    print("Point macOS Web + Secure Web proxy here. Leave SOCKS off. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
