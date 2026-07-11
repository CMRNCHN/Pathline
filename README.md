# PromptPath

Privacy-first, client-mediated call orchestration. v1 minimizes trust in PromptPath infrastructure by keeping secrets, phone numbers, and audio on the user's device.

See [PromptPath Architecture.md](./PromptPath%20Architecture.md) for the canonical security spec.

## v1 Architecture

```
Device (native / web shell)
  ├── Consent + secrets (local only)
  ├── Native dialer / tel: handoff
  ├── Local STT (Web Speech / Whisper)
  └── Encrypted status blob ──► Thin API (:8000)
                                    ├── Ephemeral JWT auth
                                    ├── Hashed session IDs
                                    ├── Auto-purge
                                    └── Revoke / export / delete
```

**Server-mediated calls are deferred to v3.** See [docs/roadmap.md](./docs/roadmap.md).

## Quick Start

### First-time setup

**From the repo root** (not `client/`). Replace the path with wherever you cloned PromptPath — e.g. `~/Developer/projects/PromptPath` on a Mac, or `/workspace` in this cloud VM:

```bash
cd ~/Developer/projects/PromptPath   # your real path — not literally /path/to/PromptPath
npm run install
```

`npm run install` picks the right launcher for your OS:

| OS | What it does |
|----|----------------|
| **macOS** | Builds `PromptPath.app` with icon, links `~/Applications`, **pins to Dock** |
| **Linux** | Installs `~/.local/share/applications/promptpath.desktop` + icon (pins GNOME dock when available) |

macOS-only / Linux-only:

```bash
npm run install:mac
npm run install:linux
```

Then from **any directory**:

```bash
promptpath          # start in terminal (Ctrl+C to stop)
promptpath-stop     # stop background services
```

Or **Dock** / **Spotlight** (macOS) or **app launcher** (Linux) → **PromptPath**.

**Headless Linux** (cloud VM, SSH, no desktop): the `.desktop` file is installed but there is no dock to pin. Use `./scripts/start.sh` or open http://localhost:3000 after starting.

### macOS apps (in project folder)

| App | Action |
|-----|--------|
| `PromptPath.app` | Start API + client, open browser |
| `PromptPath Stop.app` | Stop services |

After `install-macos.sh`, these also appear in **~/Applications**.

### Terminal (must be in project folder)

If you have not run `install-macos.sh`, `cd` into the project first:

```bash
cd ~/Developer/projects/PromptPath
./PromptPath          # foreground
npm start             # same
./scripts/stop.sh     # stop
```

Logs: `.logs/api.log` and `.logs/client.log`

Or manually:

```bash
cp .env.example .env

# API
python3 -m venv .venv && source .venv/bin/activate
pip install -e packages/shared-python -e services/api
uvicorn promptpath_api.main:app --reload --port 8000

# Client (separate terminal)
cd client && npm install && npm run dev
```

Or with Docker:

```bash
docker compose up --build
```

Open http://localhost:3000

## Known IVR Scripts

Automated privacy-preserving status checks using **pre-authored scripts only** — no discovery.

- **trigger** → DTMF to send
- **response** + **key** → IVR phrase translated into `status[key]`
- Scripts live in `client/public/scripts/*.json`

See [docs/known-scripts.md](./docs/known-scripts.md).

The fill-in-the-blank **IVR Routines** builder lives in a separate repo: `../ivr-routines`.

**Shareable UI:** [`frontend-ui/`](./frontend-ui/) — standalone copy of the web client for sharing or embedding.

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/threat-model.md](./docs/threat-model.md) | Adversaries, objectives, control mapping |
| [docs/roadmap.md](./docs/roadmap.md) | v1 / v2 / v3 phases |
| [client-native/README.md](./client-native/README.md) | Native app integration contract |

## Project Structure

```
PromptPath/
├── services/
│   ├── api/              # v1 thin backend (use this)
│   └── deferred/         # v2/v3 services (not started by default)
├── client/               # Web consent + status shell
├── client-native/        # Native integration guide
├── packages/shared-python/
├── docs/
└── lab/                  # Asterisk + SIPp (docker profile: lab)

### Lab IVR (Tier C)

```bash
./scripts/lab.sh
```

Register a softphone with TLS credentials from `.env` @ `127.0.0.1:5061`, dial `1000`, run **Lab account status** in the web UI. See [docs/lab-run.md](./docs/lab-run.md).
```

## Privacy Guarantees (v1)

- Target numbers and secrets never sent to server
- Server stores only hashed session IDs + opaque encrypted blobs
- Transcripts stay local; only SHA-256 hash included in encrypted status
- Auto-purge after retention window
- User can revoke token and delete data anytime

## Residual Metadata

Carriers still see calling/called numbers, timestamps, duration, and billing metadata. This cannot be eliminated on PSTN.

## Deferred (v2/v3)

| Phase | Features |
|-------|----------|
| v2 | DID pool, multi-provider, cooldown |
| v3 | Server-mediated PJSIP orchestrator (exception path) |

See `services/deferred/README.md`.
