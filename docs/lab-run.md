# Tier C — Lab IVR test runs

Run the Pathline lab Asterisk IVR locally and drive it end-to-end from the
**desktop app**. The Tauri shell injects the pure-Rust `rsiprtp` SIP bridge
(`docs/desktop-sip-stack.md`, `LOCKED_SIP_STACK=rsiprtp`), which owns dial,
RTP media, DTMF injection, and raw inbound PCM for on-device STT
(`docs/desktop-audio-contract.md`). This is the **primary automation path** —
no softphone, no manual paste.

## What you get

| Component | Purpose |
|-----------|---------|
| **Asterisk** (Docker or native) | Multi-step lab IVR on extension `1000` |
| **Desktop app** (Tauri + `rsiprtp`) | Places the call over **SIP/TLS**, sends DTMF, and captures call audio locally |
| **API + web client** | Identity, run values, encrypted status; hosts the automated run UI |

The desktop bridge carries the call audio itself and feeds it to local STT —
you do **not** register a softphone or paste phrases in the primary flow.

> **Current status:** SIP/RTP, native Whisper, final STT flushing, lifecycle
> outcomes, phrase matching, and keypad injection are implemented and locally
> tested. `lab-verify-flow.sh` validates the loaded dialplan and completes an
> authenticated SIP/TLS IVR traversal to remote BYE. Production dialing fails
> closed without SRTP unless `PATHLINE_SIP_PROFILE=lab` on loopback. The
> remaining operator gate is one recorded interactive Tauri GUI run through
> real Asterisk media plus encrypted API submission — see
> `docs/production-acceptance.md`.

## Prerequisites

- Docker (optional — native Asterisk fallback if Docker build fails)
- Node.js 20+ and Python 3.12+
- Rust toolchain (per `desktop/src-tauri/rust-toolchain.toml`) for the Tauri shell
- CMake (required to compile the bundled whisper.cpp runtime)
- macOS 10.15+ for packaged desktop builds (required by whisper.cpp)
- On Linux, Tauri system libraries — `./scripts/install-linux-tauri-deps.sh`
  (macOS-first; see `docs/desktop-sip-stack.md`)

## Quick start (desktop — primary)

**1. Start the lab stack** (Asterisk + API + web client):

```bash
./scripts/lab.sh
```

On first run this generates:

- TLS key + self-signed cert (`lab/asterisk/generated/tls/`)
- Random `LAB_SIP_PASSWORD` in `.env` (if unset)
- Rendered PJSIP config for port **5061**

Credentials are written to `lab/asterisk/generated/credentials.env` (gitignored).

**2. Run the desktop app** (owns the call):

```bash
./desktop/src-tauri/resources/models/fetch-model.sh
npm run desktop:dev
```

The repository includes a pinned model manifest and fetch script. The model is
accepted only when its SHA-256 matches the bundled manifest; a missing or
invalid model blocks automated mode before dialing.

The desktop shell starts its own API sidecar if one is not already healthy,
then launches the Tauri window. The `rsiprtp` bridge reads SIP host and
credentials from the environment (`LAB_SIP_*` / `PATHLINE_SIP_*`; see
**SIP bridge configuration** below), so the Path only carries the dial
**target** (extension `1000`).

**3. Execute the Path:** in the desktop app open **Run** →
**Lab account status (Asterisk 1000)** and start the run. The bridge dials
`1000` over TLS, STT transcribes the IVR locally, and matched steps inject
DTMF automatically. `autoListen` is enabled in the Path so the desktop run
listens locally without manual interaction.

> **Combined shortcut:** `./scripts/lab-desktop.sh` runs steps 1–2 together
> (lab stack, then desktop dev).

## SIP bridge configuration

The bridge composes the full SIP URI as `sip:<target>@<server>` and reads
host/credentials from the environment (`desktop/src-tauri/src/sip_bridge.rs`).
The Path supplies only the dial `target` (`1000`); everything else is env:

| Variable | Source / default | Purpose |
|----------|------------------|---------|
| `LAB_SIP_SERVER` / `PATHLINE_SIP_SERVER` | `credentials.env` (default `127.0.0.1`) | SIP server host |
| `LAB_SIP_TLS_PORT` / `PATHLINE_SIP_TLS_PORT` | `credentials.env` (default `5061`) | SIP/TLS port |
| `LAB_SIP_USER` / `PATHLINE_SIP_USER` | `credentials.env` (default `pathline-lab`) | SIP auth user |
| `LAB_SIP_PASSWORD` / `PATHLINE_SIP_PASSWORD` | `credentials.env` / `.env` | SIP auth password |
| `PATHLINE_SIP_VERIFY_TLS` | unset for loopback | Verify server cert; defaults off for the self-signed localhost lab only |

`PATHLINE_SIP_*` overrides `LAB_SIP_*` when both are set. For the localhost lab
the self-signed cert is trusted automatically (loopback); never relax TLS
verification for a non-loopback / production server.

Load the generated lab credentials into the desktop dev environment before
`npm run desktop:dev`, e.g.:

```bash
set -a; source lab/asterisk/generated/credentials.env; set +a
npm run desktop:dev
```

## Run values (defaults)

| Variable | Lab default | Asterisk expects |
|----------|-------------|------------------|
| `account_pin` | `1234` | 4-digit PIN |
| `ssn_last4` | `5678` | 4-digit SSN suffix |

The Path's **Target number** is `1000` (the lab extension). Leave it as-is —
the bridge composes the SIP URI from the env above.

## Verify without a call

Fast, non-interactive preflight + phrase-matching smoke test:

```bash
./scripts/lab-verify-flow.sh
```

This fails fast with a clear message if the API (`http://127.0.0.1:8000/health`)
or the lab Asterisk SIP/TLS port (`5061`) is not up, then replays the IVR
prompts through the flow navigator to confirm phrase → DTMF mapping.

## Legacy fallback: softphone + manual paste (browser)

Use this **only** when the desktop bridge is unavailable (e.g. no Rust
toolchain, or debugging signaling). It is not the supported automation path
and does not exercise the `rsiprtp` bridge or local STT.

1. Start the lab stack: `./scripts/lab.sh`, then open
   http://localhost:3000 → **Run** → **Lab account status (Asterisk 1000)**.
2. Register a SIP softphone (Linphone, Zoiper, etc.) over **TLS**:

   | Setting | Value |
   |---------|-------|
   | Transport | **TLS** |
   | Server | `127.0.0.1` |
   | Port | `5061` (or `LAB_SIP_TLS_PORT` in `.env`) |
   | Username | `LAB_SIP_USER` from `.env` (default `pathline-lab`) |
   | Password | `LAB_SIP_PASSWORD` from `.env` |
   | Certificate | Accept self-signed / trust lab cert |

3. Dial **`1000`**, then paste what you hear into the Listen box and send DTMF
   from the softphone.

> **Do not use `lab/lab` or UDP 5060** — those were removed for the production
> privacy stack.

### Phrase cheat sheet (legacy paste)

| Step | Paste when you hear… | DTMF on softphone |
|------|----------------------|-------------------|
| Main menu | `account` | `1` |
| Touch tone | `touch tone` | `9` |
| PIN | `pin` | `1234#` |
| SSN | `last four` | `5678#` |
| Status menu | `balance` | `1` |
| Readout | `your dollars` or `1234` | — |
| End | `goodbye` | — |

## Stop lab services

```bash
./scripts/stop.sh
docker compose --profile lab stop asterisk   # if using Docker
sudo asterisk -rx "core stop now"           # if using native Asterisk
```

## Troubleshooting

**Desktop bridge won't connect on TLS**
Confirm `./scripts/lab.sh` reported `Asterisk SIP/TLS listening on
127.0.0.1:5061` and that `lab/asterisk/generated/credentials.env` was sourced
into the `npm run desktop:dev` environment. For loopback the self-signed cert
is trusted automatically.

**Softphone won't register on TLS (legacy)**
Enable TLS transport, port 5061, and allow the self-signed certificate. Check
`lab/asterisk/generated/credentials.env` for the current password.

**Upgraded from old lab/lab setup**
Remove the `# Pathline lab block` section from `/etc/asterisk/pjsip.conf` if
using native Asterisk, then re-run `./scripts/lab.sh`.

**No audio**
Ensure RTP ports `10000-10100/udp` are open (Docker maps these automatically).

## References

- SIP stack decision (pure-Rust `rsiprtp`): `docs/desktop-sip-stack.md`
- PCM audio-frame contract (bridge → STT): `docs/desktop-audio-contract.md`
- Architecture boundary: `docs/architecture-boundary.md`
