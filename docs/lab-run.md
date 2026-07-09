# Tier C — Lab IVR test runs

Run the PromptPath lab Asterisk IVR locally with a SIP softphone (TLS) and the web UI for phrase matching.

## What you get

| Component | Purpose |
|-----------|---------|
| **Asterisk** (Docker or native) | Multi-step lab IVR on extension `1000` |
| **Softphone** | Places the call over **SIP/TLS** and sends DTMF |
| **Web UI** | Consent, run values, paste IVR phrases, encrypted status |

The web app does **not** carry call audio. You hear the IVR on the softphone and paste what you hear into the Listen box.

## Prerequisites

- Docker (optional — native Asterisk fallback if Docker build fails)
- Node.js 20+ and Python 3.12+
- A SIP softphone with **TLS** support: Linphone, Zoiper, etc.

## Quick start

```bash
./scripts/lab.sh
```

On first run this generates:

- TLS key + self-signed cert (`lab/asterisk/generated/tls/`)
- Random `LAB_SIP_PASSWORD` in `.env` (if unset)
- Rendered PJSIP config for port **5061**

Credentials are written to `lab/asterisk/generated/credentials.env` (gitignored).

Open http://localhost:3000 → **Run** → **Lab account status (Asterisk 1000)**.

## Softphone setup

| Setting | Value |
|---------|-------|
| Transport | **TLS** |
| Server | `127.0.0.1` |
| Port | `5061` (or `LAB_SIP_TLS_PORT` in `.env`) |
| Username | `LAB_SIP_USER` from `.env` (default `promptpath-lab`) |
| Password | `LAB_SIP_PASSWORD` from `.env` |
| Certificate | Accept self-signed / trust lab cert |

Register, then dial **`1000`**.

> **Do not use `lab/lab` or UDP 5060** — those were removed for the production privacy stack.

## Run values (defaults)

| Variable | Lab default | Asterisk expects |
|----------|-------------|------------------|
| `account_pin` | `1234` | 4-digit PIN |
| `ssn_last4` | `5678` | 4-digit SSN suffix |

Leave **Target number** empty — dial from the softphone.

## Phrase cheat sheet

| Step | Paste when you hear… | DTMF on softphone |
|------|----------------------|-------------------|
| Main menu | `account` | `1` |
| Touch tone | `touch tone` | `9` |
| PIN | `pin` | `1234#` |
| SSN | `last four` | `5678#` |
| Status menu | `balance` | `1` |
| Readout | `your dollars` or `1234` | — |
| End | `goodbye` | — |

## Verify without a phone

```bash
./scripts/lab-verify-flow.sh
```

## Stop lab services

```bash
./scripts/stop.sh
docker compose --profile lab stop asterisk   # if using Docker
sudo asterisk -rx "core stop now"           # if using native Asterisk
```

## Troubleshooting

**Softphone won't register on TLS**  
Enable TLS transport, port 5061, and allow the self-signed certificate. Check `lab/asterisk/generated/credentials.env` for the current password.

**Upgraded from old lab/lab setup**  
Remove the `# PromptPath lab block` section from `/etc/asterisk/pjsip.conf` if using native Asterisk, then re-run `./scripts/lab.sh`.

**No audio**  
Ensure RTP ports `10000-10100/udp` are open (Docker maps these automatically).
