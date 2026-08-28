#!/usr/bin/env python3
"""Local GUI to apply a Byteful SOCKS proxy to macOS System Settings."""

from __future__ import annotations

import argparse
import json
import platform
import re
import secrets
import shlex
import socket
import threading
import urllib.parse
import webbrowser
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterable

DEFAULT_HOST = "residential.byteful.com"
DEFAULT_PORT = 8000
BYPASS_DOMAINS = ["127.0.0.1", "localhost", "*.local", "::1"]
TEST_URL = "https://api.ipify.org"
IS_MAC = platform.system() == "Darwin"


@dataclass
class ProxySpec:
    host: str
    port: int
    username: str = ""
    password: str = ""
    scheme: str = "socks5h"


class ParseError(ValueError):
    pass


def _unquote(value: str) -> str:
    return urllib.parse.unquote(value or "")


def parse_proxy_string(raw: str) -> ProxySpec:
    """Parse a Byteful (or generic) proxy string into host/port/user/pass."""
    text = (raw or "").strip().strip('"').strip("'")
    if not text:
        raise ParseError("Paste a Byteful proxy string first.")
    text = text.splitlines()[0].strip().strip('"').strip("'")
    text = text.rstrip("/")

    if "://" in text.split("@", 1)[-1] or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        return _parse_url(text)

    if re.match(r"^[^/\s]+:\d+:", text):
        host, port_s, user, password = text.split(":", 3)
        return _spec(host, port_s, user, password)

    if "@" in text:
        return _parse_url("socks5h://" + text)

    if ":" in text:
        host, port_s = text.rsplit(":", 1)
        return _spec(host, port_s, "", "")

    raise ParseError("Could not parse that proxy string.")


def _parse_url(text: str) -> ProxySpec:
    parsed = urllib.parse.urlsplit(text)
    if not parsed.hostname:
        raise ParseError("Proxy URL is missing a hostname.")
    port = parsed.port or DEFAULT_PORT
    scheme = (parsed.scheme or "socks5h").lower()
    if scheme in {"socks", "socks5"}:
        scheme = "socks5h"
    elif scheme in {"http", "https"}:
        scheme = "socks5h"
    return _spec(
        parsed.hostname,
        str(port),
        _unquote(parsed.username or ""),
        _unquote(parsed.password or ""),
        scheme,
    )


def _spec(host: str, port_s: str, username: str, password: str, scheme: str = "socks5h") -> ProxySpec:
    host = (host or "").strip().strip("[]")
    if not host:
        raise ParseError("Hostname is missing.")
    try:
        port = int(port_s)
    except (TypeError, ValueError) as exc:
        raise ParseError("Port must be a number.") from exc
    if not 1 <= port <= 65535:
        raise ParseError("Port must be between 1 and 65535.")
    return ProxySpec(
        host=host,
        port=port,
        username=_unquote(username.strip()),
        password=_unquote(password),
        scheme=scheme or "socks5h",
    )


def spec_from_fields(host: str, port: str | int, username: str, password: str) -> ProxySpec:
    return _spec(host, str(port).strip(), username, password)


def network_services() -> list[str]:
    output = _run(["networksetup", "-listallnetworkservices"], check=True).stdout
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    services: list[str] = []
    for line in lines:
        if line.startswith("An asterisk"):
            continue
        if line.startswith("*"):
            continue
        services.append(line)
    return services


def active_network_service() -> str | None:
    try:
        route = _run(["route", "-n", "get", "default"], check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    device = ""
    for line in route.splitlines():
        if "interface:" in line:
            device = line.split(":", 1)[1].strip()
            break
    if not device:
        return None
    try:
        order = _run(["networksetup", "-listnetworkserviceorder"], check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    pattern = re.compile(
        r"\((\d+)\)\s+(.*)\n\(Hardware Port:.*,\s*Device:\s*" + re.escape(device) + r"\)",
        re.MULTILINE,
    )
    match = pattern.search(order)
    if match:
        return match.group(2).strip()
    return None


def services_for_scope(scope: str) -> list[str]:
    all_services = network_services()
    if not all_services:
        raise RuntimeError("No enabled network services were found.")
    if scope == "active":
        active = active_network_service()
        if active and active in all_services:
            return [active]
        return all_services[:1]
    return all_services


def apply_commands(spec: ProxySpec, services: Iterable[str]) -> list[list[str]]:
    commands: list[list[str]] = []
    auth = ["on", spec.username, spec.password] if spec.username else ["off"]
    for service in services:
        commands.extend(
            [
                ["networksetup", "-setproxyautodiscovery", service, "off"],
                ["networksetup", "-setautoproxystate", service, "off"],
                ["networksetup", "-setwebproxystate", service, "off"],
                ["networksetup", "-setsecurewebproxystate", service, "off"],
                ["networksetup", "-setftpproxystate", service, "off"],
                ["networksetup", "-setstreamingproxystate", service, "off"],
                ["networksetup", "-setgopherproxystate", service, "off"],
                ["networksetup", "-setsocksfirewallproxy", service, spec.host, str(spec.port), *auth],
                ["networksetup", "-setsocksfirewallproxystate", service, "on"],
                ["networksetup", "-setproxybypassdomains", service, *BYPASS_DOMAINS],
            ]
        )
    return commands


def off_commands(services: Iterable[str]) -> list[list[str]]:
    return [["networksetup", "-setsocksfirewallproxystate", service, "off"] for service in services]


def socks_status(services: Iterable[str]) -> list[dict[str, str]]:
    rows = []
    for service in services:
        try:
            out = _run(["networksetup", "-getsocksfirewallproxy", service], check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            rows.append({"service": service, "detail": str(exc)})
            continue
        rows.append({"service": service, "detail": out})
    return rows


def apply_spec(spec: ProxySpec, scope: str) -> dict:
    if not IS_MAC:
        services = ["Wi-Fi"]
        commands = apply_commands(spec, services)
        return {
            "ok": False,
            "error": "This helper only writes macOS System Settings. Run it on your MacBook.",
            "would_run": _public_commands(commands),
            "services": services,
        }
    services = services_for_scope(scope)
    results = _run_all(apply_commands(spec, services))
    return {"ok": True, "services": services, "results": results}


def disable_proxy(scope: str) -> dict:
    if not IS_MAC:
        services = ["Wi-Fi"]
        return {
            "ok": False,
            "error": "This helper only writes macOS System Settings. Run it on your MacBook.",
            "would_run": _public_commands(off_commands(services)),
            "services": services,
        }
    services = services_for_scope(scope)
    results = _run_all(off_commands(services))
    return {"ok": True, "services": services, "results": results}


def current_status(scope: str) -> dict:
    if not IS_MAC:
        return {"ok": True, "macos": False, "services": [], "note": "Not running on macOS."}
    services = services_for_scope(scope)
    return {"ok": True, "macos": True, "scope": scope, "socks": socks_status(services)}


def test_proxy(spec: ProxySpec) -> dict:
    cmd = [
        "curl",
        "-sS",
        "-m",
        "20",
        "--proxy",
        f"socks5h://{spec.host}:{spec.port}",
    ]
    if spec.username:
        cmd.extend(["--proxy-user", f"{spec.username}:{spec.password}"])
    cmd.append(TEST_URL)
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=25, check=False)
    except FileNotFoundError:
        return {"ok": False, "error": "curl is not installed. macOS includes curl by default."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "The test timed out talking to Byteful."}
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "curl failed").strip()
        return {"ok": False, "error": _redact(err, spec)}
    ip = (completed.stdout or "").strip()
    if not re.match(r"^[0-9a-fA-F:.]+$", ip):
        return {"ok": False, "error": "Unexpected test response from the proxy."}
    return {"ok": True, "exit_ip": ip, "via": f"socks5h://{spec.host}:{spec.port}"}


def _redact(text: str, spec: ProxySpec) -> str:
    redacted = text
    if spec.password:
        redacted = redacted.replace(spec.password, "***")
    if spec.username:
        redacted = redacted.replace(spec.username, spec.username[:2] + "***")
    return redacted


def _public_commands(commands: list[list[str]]) -> list[str]:
    public = []
    for cmd in commands:
        shown = list(cmd)
        if "-setsocksfirewallproxy" in shown and len(shown) >= 8 and shown[-3] == "on":
            shown[-1] = "***"
        public.append(shlex.join(shown))
    return public


def _run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _run_all(commands: list[list[str]]) -> list[str]:
    lines: list[str] = []
    needs_admin = False
    for cmd in commands:
        completed = _run(cmd)
        if completed.returncode != 0 and _needs_admin(completed):
            needs_admin = True
            break
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "command failed").strip()
            raise RuntimeError(f"{shlex.join(_public_cmd(cmd))}\n{detail}")
        summary = cmd[1] if len(cmd) > 1 else cmd[0]
        service = cmd[2] if len(cmd) > 2 else ""
        lines.append(f"{summary} {service}".strip())
    if not needs_admin:
        return lines
    joined = " && ".join(shlex.join(cmd) for cmd in commands)
    script = f"do shell script {json.dumps(joined)} with administrator privileges"
    completed = _run(["osascript", "-e", script])
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "administrator command failed").strip()
        raise RuntimeError(detail)
    return [f"{cmd[1]} {cmd[2]}".strip() for cmd in commands if len(cmd) > 2]


def _public_cmd(cmd: list[str]) -> list[str]:
    shown = list(cmd)
    if "-setsocksfirewallproxy" in shown and len(shown) >= 8 and shown[-3] == "on":
        shown[-1] = "***"
    return shown


def _needs_admin(completed: subprocess.CompletedProcess[str]) -> bool:
    blob = f"{completed.stderr} {completed.stdout}".lower()
    return any(token in blob for token in ("permission", "authorized", "privileges", "denied"))


PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Byteful Mac Proxy</title>
  <style>
    :root {
      --bg: #ece7dc;
      --ink: #1c1915;
      --muted: #6b645a;
      --card: #fffaf3;
      --line: #ddd4c6;
      --accent: #0f6b4c;
      --accent-ink: #f4fff8;
      --danger: #8a2b1e;
      --danger-bg: #f8e8e4;
      --ok: #0f6b4c;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; }
    body {
      font: 15px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 500px at 10% -10%, #f7f1e4 0%, transparent 55%),
        var(--bg);
      min-height: 100vh;
    }
    main {
      max-width: 560px;
      margin: 0 auto;
      padding: 36px 20px 48px;
    }
    h1 {
      font-size: 28px;
      letter-spacing: -0.03em;
      margin: 0 0 4px;
    }
    .lede { color: var(--muted); margin: 0 0 22px; }
    form {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 18px 40px rgba(70, 50, 20, 0.08);
    }
    label {
      display: block;
      font-size: 12px;
      font-weight: 650;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 6px;
    }
    textarea, input, select {
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 10px;
      padding: 10px 12px;
      font: inherit;
    }
    textarea { min-height: 72px; resize: vertical; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
    .row { display: grid; grid-template-columns: 1fr 120px; gap: 12px; }
    .stack { margin-bottom: 14px; }
    .hint { margin: 6px 0 0; color: var(--muted); font-size: 12px; }
    .scope {
      display: flex;
      gap: 8px;
      background: #f3eee4;
      padding: 4px;
      border-radius: 12px;
    }
    .scope label {
      flex: 1;
      margin: 0;
      text-transform: none;
      letter-spacing: 0;
      font-size: 13px;
      font-weight: 600;
      color: var(--ink);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 8px 6px;
      border-radius: 9px;
      cursor: pointer;
    }
    .scope input { width: auto; accent-color: var(--accent); }
    .scope label:has(input:checked) { background: #fff; }
    .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
    button {
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }
    button.primary { background: var(--accent); color: var(--accent-ink); }
    button.secondary { background: #efe8db; color: var(--ink); }
    button.danger { background: var(--danger-bg); color: var(--danger); }
    button:disabled { opacity: 0.6; cursor: wait; }
    #log {
      margin-top: 16px;
      background: #1c1915;
      color: #efe8db;
      border-radius: 12px;
      padding: 12px 14px;
      min-height: 92px;
      font: 12.5px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }
    #log.ok { box-shadow: inset 3px 0 0 var(--ok); }
    #log.err { box-shadow: inset 3px 0 0 var(--danger); }
    footer { margin-top: 16px; color: var(--muted); font-size: 12.5px; }
  </style>
</head>
<body>
  <main>
    <h1>Byteful Mac Proxy</h1>
    <p class="lede">Paste a residential proxy from Byteful. This writes SOCKS into macOS System Settings for the selected network services.</p>
    <form id="form">
      <div class="stack">
        <label for="raw">Byteful proxy string</label>
        <textarea id="raw" placeholder="residential.byteful.com:8000:username:password" autocomplete="off" spellcheck="false"></textarea>
        <p class="hint">Also accepts socks5h://user:pass@host:port and user:pass@host:port.</p>
      </div>
      <div class="row stack">
        <div>
          <label for="host">Server</label>
          <input id="host" value="residential.byteful.com" autocomplete="off" />
        </div>
        <div>
          <label for="port">Port</label>
          <input id="port" value="8000" inputmode="numeric" />
        </div>
      </div>
      <div class="stack">
        <label for="username">Username</label>
        <input id="username" autocomplete="off" placeholder="account user, plus any _c_ / _s_ targeting" />
      </div>
      <div class="stack">
        <label for="password">Password</label>
        <input id="password" type="password" autocomplete="off" />
      </div>
      <div class="stack">
        <label>Apply to</label>
        <div class="scope">
          <label><input type="radio" name="scope" value="all" checked /> Entire Mac (all services)</label>
          <label><input type="radio" name="scope" value="active" /> Active network only</label>
        </div>
      </div>
      <div class="actions">
        <button class="primary" type="submit">Apply to this Mac</button>
        <button class="secondary" id="test" type="button">Test SOCKS5h</button>
        <button class="danger" id="off" type="button">Turn proxy off</button>
      </div>
      <div id="log">Ready. Paste a Byteful string, then apply.</div>
    </form>
    <footer>
      Byteful auto-detects HTTP vs SOCKS on the same host:port. This app always enables the macOS SOCKS proxy.
      Safari and most system apps follow that setting. Some apps ignore it. macOS still resolves some DNS locally;
      the Test button uses SOCKS5h (remote DNS) through curl.
    </footer>
  </main>
  <script>
    const token = new URLSearchParams(location.search).get("token") || "";
    const logEl = document.getElementById("log");
    const rawEl = document.getElementById("raw");

    function log(msg, kind) {
      logEl.textContent = msg;
      logEl.className = kind || "";
    }
    function payload() {
      return {
        raw: rawEl.value,
        host: document.getElementById("host").value,
        port: document.getElementById("port").value,
        username: document.getElementById("username").value,
        password: document.getElementById("password").value,
        scope: document.querySelector("input[name=scope]:checked").value
      };
    }
    async function api(path, body) {
      const res = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Token": token },
        body: JSON.stringify(body || payload())
      });
      const data = await res.json();
      if (!res.ok || data.ok === false) {
        let msg = data.error || ("Request failed (" + res.status + ")");
        if (data.would_run && data.would_run.length) {
          msg += "\\n\\nCommands that would run on a Mac:\\n" + data.would_run.join("\\n");
        }
        throw new Error(msg);
      }
      return data;
    }
    async function parsePaste() {
      const raw = rawEl.value.trim();
      if (!raw) return;
      try {
        const data = await api("/api/parse", { raw });
        document.getElementById("host").value = data.host;
        document.getElementById("port").value = data.port;
        document.getElementById("username").value = data.username || "";
        document.getElementById("password").value = data.password || "";
        log("Parsed " + data.host + ":" + data.port + (data.username ? " as " + data.username : "") + ".", "ok");
      } catch (err) {
        log(err.message, "err");
      }
    }
    rawEl.addEventListener("paste", () => setTimeout(parsePaste, 0));
    rawEl.addEventListener("blur", parsePaste);
    document.getElementById("form").addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        log("Applying SOCKS proxy…");
        const data = await api("/api/apply");
        const extra = (data.would_run || []).join("\\n");
        log("Applied SOCKS on: " + (data.services || []).join(", ") + (extra ? "\\n" + extra : ""), "ok");
      } catch (err) {
        log(err.message, "err");
      }
    });
    document.getElementById("test").addEventListener("click", async () => {
      try {
        log("Testing SOCKS5h through Byteful…");
        const data = await api("/api/test");
        log("Proxy is working. Exit IP: " + data.exit_ip + "\\n" + data.via, "ok");
      } catch (err) {
        log(err.message, "err");
      }
    });
    document.getElementById("off").addEventListener("click", async () => {
      try {
        log("Turning SOCKS proxy off…");
        const data = await api("/api/off");
        log("SOCKS proxy off on: " + (data.services || []).join(", "), "ok");
      } catch (err) {
        log(err.message, "err");
      }
    });
    fetch("/api/status?scope=all", { headers: { "X-Token": token } })
      .then((res) => res.json())
      .then((data) => {
        if (data.macos === false) {
          log("GUI is up. Apply will only succeed on a MacBook.", "");
        }
      })
      .catch(() => {});
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "BytefulMacProxy/1.0"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _token(self) -> str:
        return getattr(self.server, "token")  # type: ignore[attr-defined]

    def _authorized(self) -> bool:
        header = self.headers.get("X-Token", "")
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        token = header or (query.get("token") or [""])[0]
        return secrets.compare_digest(token, self._token())

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if not self._authorized():
            self._json(403, {"ok": False, "error": "Missing GUI token. Open the URL this app printed."})
            return
        if parsed.path in {"/", "/index.html"}:
            body = PAGE_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/status":
            scope = urllib.parse.parse_qs(parsed.query).get("scope", ["all"])[0]
            try:
                self._json(200, current_status(scope))
            except Exception as exc:  # noqa: BLE001 — surface to the GUI
                self._json(400, {"ok": False, "error": str(exc)})
            return
        self._json(404, {"ok": False, "error": "Not found."})

    def do_POST(self) -> None:
        if not self._authorized():
            self._json(403, {"ok": False, "error": "Missing GUI token. Open the URL this app printed."})
            return
        parsed = urllib.parse.urlparse(self.path)
        try:
            data = self._read_json()
            spec = _spec_from_request(data)
            if parsed.path == "/api/parse":
                parsed_spec = parse_proxy_string(data.get("raw") or "")
                payload = asdict(parsed_spec)
                self._json(200, {"ok": True, **payload})
                return
            if parsed.path == "/api/apply":
                result = apply_spec(spec, data.get("scope") or "all")
                status = 200 if result.get("ok") else 400
                self._json(status, result)
                return
            if parsed.path == "/api/off":
                result = disable_proxy(data.get("scope") or "all")
                status = 200 if result.get("ok") else 400
                self._json(status, result)
                return
            if parsed.path == "/api/test":
                result = test_proxy(spec)
                status = 200 if result.get("ok") else 400
                self._json(status, result)
                return
        except ParseError as exc:
            self._json(400, {"ok": False, "error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001 — surface to the GUI
            self._json(400, {"ok": False, "error": str(exc)})
            return
        self._json(404, {"ok": False, "error": "Not found."})

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ParseError("Invalid request body.")
        return data

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def _spec_from_request(data: dict) -> ProxySpec:
    raw = (data.get("raw") or "").strip()
    host = (data.get("host") or "").strip()
    port = data.get("port") or ""
    username = data.get("username") or ""
    password = data.get("password") or ""
    if host and str(port).strip():
        return spec_from_fields(host, port, username, password)
    if raw:
        return parse_proxy_string(raw)
    raise ParseError("Enter a Byteful server and port, or paste a proxy string.")


def pick_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])


def serve(port: int, open_browser: bool) -> None:
    token = secrets.token_urlsafe(24)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.token = token  # type: ignore[attr-defined]
    url = f"http://127.0.0.1:{port}/?token={token}"
    print(f"Byteful Mac Proxy GUI: {url}")
    print("Leave this terminal open. Press Ctrl+C to quit.")
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()


SELF_TESTS = [
    (
        "residential.byteful.com:8000:stevejobs:apple123",
        ProxySpec("residential.byteful.com", 8000, "stevejobs", "apple123"),
    ),
    (
        "residential.byteful.com:8000:stevejobs_s_we12NkllMSS:apple123",
        ProxySpec("residential.byteful.com", 8000, "stevejobs_s_we12NkllMSS", "apple123"),
    ),
    (
        "residential.byteful.com:8683:user_123:pass@123",
        ProxySpec("residential.byteful.com", 8683, "user_123", "pass@123"),
    ),
    (
        "socks5h://stevejobs:apple123@residential.byteful.com:8000",
        ProxySpec("residential.byteful.com", 8000, "stevejobs", "apple123"),
    ),
    (
        "socks5://user123_s_TMEK5I970J0IC4QJ:abc123@residential.byteful.com:8864",
        ProxySpec("residential.byteful.com", 8864, "user123_s_TMEK5I970J0IC4QJ", "abc123"),
    ),
    (
        "stevejobs:apple123@residential.byteful.com:8000",
        ProxySpec("residential.byteful.com", 8000, "stevejobs", "apple123"),
    ),
    (
        "http://stevejobs:p%40ss@residential.byteful.com:8000",
        ProxySpec("residential.byteful.com", 8000, "stevejobs", "p@ss"),
    ),
    (
        "  'residential.byteful.com:8000:stevejobs:apple:123'  ",
        ProxySpec("residential.byteful.com", 8000, "stevejobs", "apple:123"),
    ),
    (
        "residential.byteful.com:8000",
        ProxySpec("residential.byteful.com", 8000, "", ""),
    ),
]


def self_test() -> int:
    failed = 0
    for raw, expected in SELF_TESTS:
        got = parse_proxy_string(raw)
        if got != expected:
            failed += 1
            print(f"FAIL {raw!r}\n  got      {got}\n  expected {expected}")
    cmds = apply_commands(ProxySpec("residential.byteful.com", 8000, "stevejobs", "secret"), ["Wi-Fi"])
    if not any(cmd[1] == "-setsocksfirewallproxy" and "secret" in cmd for cmd in cmds):
        failed += 1
        print("FAIL apply_commands did not include authenticated SOCKS setup")
    public = _public_commands(cmds)
    if any("secret" in line for line in public):
        failed += 1
        print("FAIL password leaked in public command list")
    if failed:
        print(f"{failed} self-test(s) failed")
        return 1
    print(f"{len(SELF_TESTS)} parser cases plus command redaction passed")
    return 0


def cli_apply(raw: str, scope: str) -> int:
    spec = parse_proxy_string(raw)
    result = apply_spec(spec, scope)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def cli_off(scope: str) -> int:
    result = disable_proxy(scope)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a Byteful SOCKS proxy to this Mac.")
    parser.add_argument("--port", type=int, default=8765, help="Local GUI port (default 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser window")
    parser.add_argument("--self-test", action="store_true", help="Run parser tests and exit")
    parser.add_argument("--apply", metavar="PROXY", help="Apply a proxy string without the GUI")
    parser.add_argument("--off", action="store_true", help="Turn the SOCKS proxy off without the GUI")
    parser.add_argument(
        "--scope",
        choices=("all", "active"),
        default="all",
        help="Network services to change (default all)",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.apply:
        return cli_apply(args.apply, args.scope)
    if args.off:
        return cli_off(args.scope)
    port = pick_port(args.port)
    serve(port, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
