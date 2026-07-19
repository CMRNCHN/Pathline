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
- Native `window.__pathlineWhisper` implementation + bundled local model.
- Valid Asterisk IVR routing: `extensions_lab.conf` currently uses context-style
  `Goto(name,s,1)` calls for extensions in `[lab-ivr]` and defines extension `1`
  twice, so the lab cannot traverse its intended states.
- Transport lifecycle wiring: SIP `error` / `disconnected` events must end or
  fail the active Run, and buffered STT must flush on disconnect.
- Fail-closed transport selection: Tauri must not silently use
  `SimulatorTransport` when the native SIP bridge is absent.
- One recorded macOS/Tauri/Asterisk dial → RTP → local STT → keypad → encrypted
  callstate acceptance run.

`./scripts/start.sh` (aka `npm start`) starts API + browser UI only. It is useful
for authoring/manual fallback, but it does not start the production automation
endpoint. `Ctrl+C` (or `./scripts/stop.sh`) stops background services. Logs:
`.logs/api.log`, `.logs/client.log`.

### Non-obvious caveats
- **Python venv package is required**: creating `.venv` needs the OS `python3.12-venv` package
  (apt). Without it `python3 -m venv` fails with an `ensurepip` error. This is installed as a system
  dependency (not by the update script).
- **Python deps are editable installs** of `packages/shared-python` + `services/api` into `.venv`
  (there is no `requirements.txt`). Re-run `pip install -e packages/shared-python -e services/api`
  inside the venv after pulling dependency changes; the update script does this.
- The client dev server proxies `/api` → `http://127.0.0.1:8000` (see `client/vite.config.ts`);
  in dev `VITE_API_URL` is `/api`. Start the API before/with the client for run flows to work.
- **No lint or automated test framework is configured** (no ESLint/Prettier/pytest/jest, no CI).
  Type-checking runs implicitly via `tsc` during `cd client && npm run build`. `scripts/test-navigator.py`
  is an ad-hoc manual script, not a test suite.
- Secrets: `start.sh` auto-generates `JWT_SECRET` / `SESSION_PEPPER` per run via `openssl rand`.
  The DB defaults to local SQLite (`pathline.db`); no external DB needed for v1.
- Automated calls require the desktop-native SIP transport. A plain browser run
  is **manual fallback only** — paste IVR phrases and follow the on-screen keypad
  guide. The desktop app must fail closed when native SIP or local STT is
  unavailable; it must not silently substitute browser speech or a simulated
  call for a production Run.
