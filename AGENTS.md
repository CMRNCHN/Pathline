# Pathline

Privacy-first, client-mediated call orchestration. See `README.md` and `Pathline Architecture.md`.

## Cursor Cloud specific instructions

### Working agreement
- **Always merge AGENTS.md updates.** The maintainer wants changes to this file kept and merged
  every time, so future agents retain these learnings. Always include AGENTS.md edits in the PR and
  explicitly flag them for merge. (Agents cannot merge PRs themselves; a human must click merge.)
- **Failed Run loop (every prompt):** when the user reports a failed Run / Call failed / SIP error,
  proactively run `.cursor/agents/run-failure-logger` then `.cursor/agents/run-failure-fixer`
  (see `.cursor/rules/run-failure-loop.mdc`). Logger first (evidence), fixer second (minimal fix).

### Scope
The shipping **v1 production automation endpoint is the native desktop app**:
the Tauri/Rust shell (`desktop/`) embeds the React UI (`client/`) and owns SIP/RTP,
local STT, phrase matching, keypad injection, and the on-device audit ledger. The
FastAPI service (`services/api`) remains thin: identity plus encrypted artifact
storage only.

The React UI in `client/` is embedded in the desktop webview. Do not treat a
standalone browser as a supported app surface for day-to-day work. Never move
call audio, transcripts, phone numbers, secrets, or orchestration into the
server to make a browser automate calls.

`frontend-ui/`, external-softphone flows, and `services/deferred/*` are not part
of the shipping path. The SIP `lab/` (Asterisk/Docker) is development-only test
infrastructure. `client-native/` is docs only.

### Services (v1)
| Service | Dir | Dev command | URL |
|---------|-----|-------------|-----|
| Desktop app (primary) | `desktop` + `client` | `npm start` → `./scripts/lab-desktop.sh` | Native Pathline window |
| Desktop only (API already up) | `desktop` + `client` | `npm run desktop:dev` | Native Pathline window |
| API (FastAPI/uvicorn) | `services/api` | started by desktop/lab scripts | http://127.0.0.1:8000 (`/health`, `/docs`) |
| Vite UI host (webview only) | `client` | started by desktop/lab scripts | http://127.0.0.1:3000 (do not open in a browser) |

`npm start` launches the lab desktop stack (Asterisk when needed, API, Vite
webview host, Tauri). Prefer that over opening the Vite URL in Safari/Chrome.
`npm run desktop:dev` is the lighter path when the API sidecar is already up.
`./scripts/start.sh` is an internal sidecar helper (API + Vite host) used by lab;
it must not open a browser. `Ctrl+C` / `./scripts/stop.sh` stops background
services. Logs: `.logs/api.log`, `.logs/client.log`.

### Current live-call blockers
Do not describe the desktop loop as live-E2E complete until all of these land:
- One recorded macOS/Tauri/Asterisk dial → RTP → local STT → keypad → encrypted
  callstate acceptance run (operator-recorded; see `docs/production-acceptance.md`).
- Production SIP trunk with SRTP — locked `rsiprtp 0.4.1` has no SRTP; dialing
  fails closed unless `PATHLINE_SIP_PROFILE=lab` on loopback.
- Apple Developer ID signing + notarization of a self-contained release DMG.

### Client IA (five surfaces)
Operator UI is exactly five top-level surfaces — no Workflows / Edit / Run /
Settings / Templates / Runs nav items:

| Surface | Job |
|---------|-----|
| Dashboard | Status, quick actions, recent activity |
| Path Library | Paths list + detail; EditForm + Run embedded |
| Accounts | Profiles; fields → Path Inputs; ready Paths |
| Input Vault | Sealed secrets; Accounts bind `vaultKey` |
| System | Runtime health + former Settings |

Skill order for UI: `frontend-ui-architect` → `frontend-structure-redesign` →
`.cursor/skills/five-surface-ia`. Agents: `five-surface-nav-shell`,
`five-surface-path-library`, `five-surface-accounts-vault`,
`five-surface-dashboard-system`. Vocabulary: **Path**, **Input Vault** (not
Workflow as the primary document name). Never write secrets into Path JSON.

**Multi-agent delivery:** start with `pathline-orchestrator` (skill
`pathline-orchestration`). Figma via `pathline-figma-design` + skill
`pathline-figma-mcp` (Figma **free/Starter**: one file, no Code Connect/Dev Mode
dependency). UX polish via `pathline-ux-upgrade`. Rule:
`.cursor/rules/pathline-work-ownership.mdc`.

### Non-obvious caveats
- **Python venv package is required**: creating `.venv` needs the OS `python3.12-venv` package
  (apt). Without it `python3 -m venv` fails with an `ensurepip` error. This is installed as a system
  dependency (not by the update script).
- **Native Whisper builds require CMake**: `whisper-rs` compiles whisper.cpp from
  source. Install CMake before `cargo test` / desktop builds, and fetch the pinned,
  checksummed model with `desktop/src-tauri/resources/models/fetch-model.sh`.
  Packaged macOS builds target 10.15+; keep `.cargo/config.toml` and
  `tauri.conf.json` deployment targets aligned or whisper.cpp release builds fail.
- **Python deps are editable installs** of `packages/shared-python` + `services/api` into `.venv`
  (there is no `requirements.txt`). Re-run `pip install -e packages/shared-python -e "services/api[test]"`
  inside the venv after pulling dependency changes; the update script does this.
- The client dev server proxies `/api` → `http://127.0.0.1:8000` (see `client/vite.config.ts`);
  in browser-dev `VITE_API_URL` is `/api`. The Tauri shell must never use that relative
  proxy path — it injects `window.__pathlineApiBase` (default `http://127.0.0.1:8000`,
  override with `PATHLINE_API_URL` at desktop build time). Fetching `/api` inside the
  webview returns HTML and WebKit reports “The string did not match the expected pattern.”
- The packaged `/Applications/Pathline.app` does not start the API by itself. Keep the
  sidecar up (`npm run desktop:dev`, `./scripts/launch-desktop.sh`, or uvicorn on :8000)
  or consent/token mint will fail. Development CORS defaults include `tauri://localhost`
  and the Vite origins; without them WKWebView shows “Load failed” on `/v1/token`.
- **Automated gates**: GitHub Actions (`.github/workflows/ci.yml`) and
  `./scripts/ci-verify.sh` cover client Vitest + build, STT fixture, API pytest +
  Alembic, Rust SIP/Whisper tests, and static lab checks. Production acceptance
  that requires Apple signing or a carrier trunk is documented in
  `docs/production-acceptance.md`.
- Secrets: `start.sh` auto-generates `JWT_SECRET` / `SESSION_PEPPER` per run via `openssl rand`.
  The DB defaults to local SQLite (`pathline.db`); production requires PostgreSQL,
  `APP_ENV=production`, and managed migrations (`AUTO_CREATE_SCHEMA=false` +
  `alembic upgrade head`). Local/dev SQLite auto-creates tables on startup and
  rebuilds when the on-disk schema predates owner-bound columns (consent/token
  mint fails with a vague WebKit “expected pattern” error until the API restarts
  against a current schema).
- Automated calls require the desktop-native SIP transport. Do not launch or
  demo the product in a standalone browser. The desktop app must fail closed
  when native SIP or local STT is unavailable; it must not silently substitute
  browser speech or a simulated call for a production Run.
- Lab dialing requires `PATHLINE_SIP_PROFILE=lab` on loopback (`lab-desktop.sh`
  sets this). Plain RTP is lab-only.
