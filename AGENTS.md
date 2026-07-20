# Pathline

Privacy-first, client-mediated call orchestration. See `README.md` and `Pathline Architecture.md`.

## Cursor Cloud specific instructions

### Working agreement
- **Always merge AGENTS.md updates.** The maintainer wants changes to this file kept and merged
  every time, so future agents retain these learnings. Always include AGENTS.md edits in the PR and
  explicitly flag them for merge. (Agents cannot merge PRs themselves; a human must click merge.)

### Scope
The shipping **v1 production automation endpoint is the native desktop app**:
the Tauri/Rust shell (`desktop/`) embeds the React UI (`client/`) and owns SIP/RTP,
local STT, phrase matching, keypad injection, and the on-device audit ledger. The
FastAPI service (`services/api`) remains thin: identity plus encrypted artifact
storage only.

The same React UI may run in a browser for authoring and manual fallback, but a
browser is **not** the telephony or automation endpoint. Never move call audio,
transcripts, phone numbers, secrets, or orchestration into the server to make the
browser automate calls.

`frontend-ui/`, external-softphone flows, and `services/deferred/*` are not part
of the shipping path. The SIP `lab/` (Asterisk/Docker) is development-only test
infrastructure. `client-native/` is docs only.

### Services (v1)
| Service | Dir | Dev command | URL |
|---------|-----|-------------|-----|
| API (FastAPI/uvicorn) | `services/api` | `source .venv/bin/activate && uvicorn pathline_api.main:app --reload --port 8000` | http://localhost:8000 (`/health`, `/docs`) |
| Desktop app (Tauri/Rust + embedded React) | `desktop` + `client` | `npm run desktop:dev` | Native Pathline window |
| Browser authoring/manual fallback | `client` | `cd client && npm run dev` | http://localhost:3000 |

For normal desktop development, run `npm run desktop:dev`; it starts/reuses the
thin API and launches the Tauri window. For a live lab call, run
`./scripts/lab-desktop.sh` to start Asterisk, API, UI, and desktop together.

### Current live-call blockers
Do not describe the desktop loop as live-E2E complete until all of these land:
- One recorded macOS/Tauri/Asterisk dial → RTP → local STT → keypad → encrypted
  callstate acceptance run (operator-recorded; see `docs/production-acceptance.md`).
- Production SIP trunk with SRTP — locked `rsiprtp 0.4.1` has no SRTP; dialing
  fails closed unless `PATHLINE_SIP_PROFILE=lab` on loopback.
- Apple Developer ID signing + notarization of a self-contained release DMG.

`./scripts/start.sh` (aka `npm start`) starts API + browser UI only. It is useful
for authoring/manual fallback, but it does not start the production automation
endpoint. `Ctrl+C` (or `./scripts/stop.sh`) stops background services. Logs:
`.logs/api.log`, `.logs/client.log`.

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
  or consent/token mint will fail.
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
- Automated calls require the desktop-native SIP transport. A plain browser run
  is **manual fallback only** — paste IVR phrases and follow the on-screen keypad
  guide. The desktop app must fail closed when native SIP or local STT is
  unavailable; it must not silently substitute browser speech or a simulated
  call for a production Run.
- Lab dialing requires `PATHLINE_SIP_PROFILE=lab` on loopback (`lab-desktop.sh`
  sets this). Plain RTP is lab-only.
