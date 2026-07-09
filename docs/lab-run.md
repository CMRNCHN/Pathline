# Tier C — Lab IVR test runs

Run the PromptPath lab Asterisk IVR locally with a SIP softphone and the web UI for phrase matching.

## What you get

| Component | Purpose |
|-----------|---------|
| **Asterisk** (Docker) | Multi-step lab IVR on extension `1000` |
| **Softphone** | Places the call and sends DTMF |
| **Web UI** | Consent, run values, paste IVR phrases, encrypted status |

The web app does **not** carry call audio. You hear the IVR on the softphone and paste what you hear into the Listen box.

## Prerequisites

- Docker (running)
- Node.js 20+ and Python 3.12+ (or use `./scripts/lab.sh` which delegates to `start.sh`)
- A SIP softphone: [Linphone](https://www.linphone.org/), [Zoiper](https://www.zoiper.com/), or similar

## Quick start

```bash
./scripts/lab.sh
```

This builds the lab Asterisk image, starts SIP on `127.0.0.1:5060`, then starts the API and web client.

Open http://localhost:3000 → **Run** → select **Lab account status (Asterisk 1000)**.

## Softphone setup

| Setting | Value |
|---------|-------|
| SIP server / domain | `127.0.0.1` |
| Port | `5060` |
| Username | `lab` |
| Password | `lab` |
| Transport | UDP |

Register, then dial **`1000`**.

## Run values (defaults)

| Variable | Lab default | Asterisk expects |
|----------|-------------|------------------|
| `account_pin` | `1234` | 4-digit PIN |
| `ssn_last4` | `5678` | 4-digit SSN suffix |

Leave **Target number** empty — the lab script does not use `tel:` handoff.

## Phrase cheat sheet

Paste these into the **Listen** box as you hear each prompt (short aliases work):

| Step | Paste when you hear… | DTMF on softphone |
|------|----------------------|-------------------|
| Main menu | `account` or `press 1 for account` | `1` |
| Touch tone | `touch tone` | `9` |
| PIN | `pin` or `enter your pin` | `1234#` (your PIN + pound) |
| SSN | `last four` or `social security` | `5678#` |
| Status menu | `balance` | `1` |
| Readout | `your dollars` or `1234` | — (captures balance phrase) |
| End | `goodbye` | — (submits encrypted status) |

The bundled script `client/public/scripts/lab-account-status.json` mirrors `flows/lab-account-status.yaml`.

## Verify without a phone

Phrase matching only (no SIP):

```bash
./scripts/lab-verify-flow.sh
```

Interactive CLI:

```bash
source .venv/bin/activate
pip install -e packages/shared-python
python scripts/test-navigator.py flows/lab-account-status.yaml
```

## Stop lab services

```bash
./scripts/stop.sh          # API + client
docker compose --profile lab stop asterisk
```

## Troubleshooting

**No audio / one-way audio**  
Ensure RTP ports `10000-10100/udp` are not blocked. The compose file maps this range for Docker.

**Softphone won't register**  
Check Asterisk logs: `docker compose --profile lab logs -f asterisk`

**Web run won't complete**  
The lab IVR plays `vm-goodbye` before hangup. Paste `goodbye` after the balance readout to trigger end + status submit.

**`tel:` opens wrong app**  
Lab script uses an empty target on purpose. Dial `1000` from the softphone manually.

## Architecture note

- YAML flow + Python `IVRNavigator` = stateful simulator (`scripts/test-navigator.py`)
- JSON script + web `runEngine` = flat phrase matcher (Run page)
- Both map to the same lab IVR prompts; the web engine does not yet share YAML state machine semantics

See also [docs/call-scripts.md](./call-scripts.md).
