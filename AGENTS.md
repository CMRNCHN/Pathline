# Pathline

Privacy-first, client-mediated call orchestration. See `README.md` and `Pathline Architecture.md`.

## Cursor Cloud specific instructions

### Scope
The shipping product is **v1**: the FastAPI backend (`services/api`) plus the web client (`client/`).
`frontend-ui/`, `desktop/` (Tauri/Rust), the SIP `lab/` (Asterisk/Docker), and `services/deferred/*`
are optional and NOT needed for normal development. `client-native/` is docs only.

### Services (v1)
| Service | Dir | Dev command | URL |
|---------|-----|-------------|-----|
| API (FastAPI/uvicorn) | `services/api` | `source .venv/bin/activate && uvicorn pathline_api.main:app --reload --port 8000` | http://localhost:8000 (`/health`, `/docs`) |
| Web client (Vite/React) | `client` | `cd client && npm run dev` | http://localhost:3000 |

Easiest: `./scripts/start.sh` (aka `npm start`) starts BOTH — it creates `.env`, ensures the venv +
editable installs, `npm install`s the client, frees ports 8000/3000, then runs uvicorn + Vite.
`Ctrl+C` (or `./scripts/stop.sh`) stops them. Logs: `.logs/api.log`, `.logs/client.log`.

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
- Automated in-browser calls require the desktop/native SIP transport; a plain browser run is
  **manual mode** — you paste IVR phrases and follow the on-screen DTMF guide. The full run flow
  still exercises the backend (token mint → session link → encrypted callstate ingest).
