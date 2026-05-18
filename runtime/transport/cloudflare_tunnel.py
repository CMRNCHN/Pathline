"""Async subprocess wrapper for Cloudflare Tunnel (cloudflared).

Usage — context manager (recommended):
    async with CloudflareTunnel(port=8081) as tunnel:
        print(tunnel.public_url)   # https://xxx.trycloudflare.com
        # ... run your server ...

Usage — manual:
    tunnel = CloudflareTunnel(port=8081)
    await tunnel.start()
    print(tunnel.public_url)
    await tunnel.stop()

Token-based (named tunnel, stable URL):
    Set CLOUDFLARE_TUNNEL_TOKEN in .env.
    The tunnel domain is configured in the Cloudflare Zero Trust dashboard.

Quick tunnel (no account required, random URL):
    Leave CLOUDFLARE_TUNNEL_TOKEN unset.
    URL is printed to stdout by cloudflared and parsed from its output.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
from types import TracebackType

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https://[a-z0-9\-]+\.trycloudflare\.com")
_NAMED_URL_RE = re.compile(r"https://[^\s]+\.cloudflareaccess\.com|https://[^\s]+\.cfargotunnel\.com")


class CloudflareTunnelError(RuntimeError):
    """Raised when cloudflared cannot be started or the URL cannot be parsed."""


class CloudflareTunnel:
    """Wraps `cloudflared tunnel` as an async subprocess.

    Env vars:
        CLOUDFLARE_TUNNEL_TOKEN — token from Zero Trust dashboard (named tunnel)
        CLOUDFLARED_BIN         — path to cloudflared binary (default: auto-detect)
    """

    def __init__(
        self,
        port: int = 8081,
        startup_timeout: float = 20.0,
    ) -> None:
        self._port = port
        self._startup_timeout = startup_timeout
        self._token = os.environ.get("CLOUDFLARE_TUNNEL_TOKEN", "")
        self._binary = os.environ.get("CLOUDFLARED_BIN") or shutil.which("cloudflared")
        self._proc: asyncio.subprocess.Process | None = None
        self._public_url: str | None = None
        self._reader_task: asyncio.Task[None] | None = None

    @property
    def public_url(self) -> str:
        if not self._public_url:
            raise CloudflareTunnelError("Tunnel not started or URL not yet available.")
        return self._public_url

    async def start(self) -> str:
        """Start cloudflared and return the public URL."""
        if not self._binary:
            raise CloudflareTunnelError(
                "cloudflared binary not found. "
                "Install with: brew install cloudflare/cloudflare/cloudflared"
            )

        if self._token:
            cmd = [self._binary, "tunnel", "run", "--token", self._token]
        else:
            cmd = [
                self._binary, "tunnel", "--url", f"http://localhost:{self._port}",
                "--no-autoupdate",
            ]

        logger.info("Starting cloudflared: %s", " ".join(cmd[:3] + ["..."]))
        self._proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        url_event: asyncio.Event = asyncio.Event()

        async def _read_output() -> None:
            assert self._proc is not None
            # cloudflared writes status to stderr for quick tunnels, stdout for named tunnels
            streams = [self._proc.stderr, self._proc.stdout]
            readers = [
                asyncio.create_task(self._drain_stream(s, url_event))
                for s in streams if s is not None
            ]
            await asyncio.gather(*readers, return_exceptions=True)

        self._reader_task = asyncio.create_task(_read_output())

        try:
            await asyncio.wait_for(url_event.wait(), timeout=self._startup_timeout)
        except asyncio.TimeoutError:
            await self.stop()
            raise CloudflareTunnelError(
                f"cloudflared did not produce a public URL within {self._startup_timeout}s"
            )

        logger.info("Cloudflare Tunnel ready: %s → localhost:%d", self._public_url, self._port)
        return self.public_url

    async def _drain_stream(
        self,
        stream: asyncio.StreamReader,
        url_event: asyncio.Event,
    ) -> None:
        async for line_bytes in stream:
            line = line_bytes.decode("utf-8", errors="replace").rstrip()
            if line:
                logger.debug("[cloudflared] %s", line)

            if not url_event.is_set():
                m = _URL_RE.search(line) or _NAMED_URL_RE.search(line)
                if m:
                    self._public_url = m.group(0)
                    url_event.set()

    async def stop(self) -> None:
        """Terminate cloudflared gracefully."""
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (asyncio.CancelledError, Exception):
                pass

        if self._proc and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._proc.kill()
            except Exception as exc:
                logger.warning("Error stopping cloudflared: %s", exc)
            finally:
                self._proc = None

        logger.info("Cloudflare Tunnel stopped")

    async def __aenter__(self) -> "CloudflareTunnel":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.stop()