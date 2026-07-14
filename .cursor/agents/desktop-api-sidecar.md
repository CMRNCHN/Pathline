---
name: desktop-api-sidecar
description: >
  Adds the desktop development launcher that starts the API sidecar
  before Tauri development. Use proactively in Wave 1 after scaffold.
  Owns only scripts/desktop-dev.sh and root package.json desktop scripts.
---

# Desktop API Sidecar Agent

## Mission

Create a deterministic developer launcher:

```
npm run desktop:dev
        |
        v
scripts/desktop-dev.sh
        |
        +--> API sidecar
        |
        +--> Tauri desktop app
```

The API remains an **external sidecar process**.
Do **not** embed API startup into Rust/Tauri.

---

## Exclusive Ownership

**Allowed edits:**

```
scripts/desktop-dev.sh
package.json
```

Root `package.json` only for `desktop:*` scripts (add/keep — do not rename unrelated scripts).

**Forbidden:**

```
client/**
desktop/src-tauri/**
services/api/**
packages/**
src/**
RunSession / engine / transport feature files
```

**Optional (allowed):**

- Verify `desktop/node_modules` exists
- Run `npm install` **only inside `desktop/`**

**Not allowed:**

- Modify client source
- Modify client package files
- Run installs that rewrite `client/package.json` / `client/package-lock.json`

---

## Branch

If the feature branch already exists remotely:

```bash
git fetch origin
git checkout -b cursor/desktop-api-sidecar-7a69 origin/cursor/desktop-api-sidecar-7a69
```

If it does not exist yet:

```bash
git fetch origin
git checkout -b cursor/desktop-api-sidecar-7a69 origin/cursor/known-scripts-and-run-automation
```

If Wave 1 is already merged into `cursor/desktop-mvp-7a69`, branch from that tip instead — still only touch the two allowed files.

---

## Requirements

### 1. API readiness (robust)

API binds only:

```
127.0.0.1:${API_PORT:-8000}
```

**API ready** means:

```
GET http://127.0.0.1:${API_PORT:-8000}/health
```

returns HTTP 200 with JSON where `"status"` is `"ok"` (see existing health handler).

Before spawning:

1. Probe health as above.
2. If ready → reuse existing process; **do not spawn**; **do not claim ownership**.
3. If unavailable → start API using **API start command resolution** below.

Port occupied but health **fails** → clear error (print remediation; do not kill foreign process).

---

### API startup wait

After spawning API, poll health:

| Parameter | Value |
|-----------|-------|
| Interval | **250ms** |
| Maximum | **30 seconds** (~120 probes) |
| Success | HTTP 200 + `{"status":"ok"}` |
| Failure | Print log location, print PID if available, exit non-zero |

Do **not** use a single `sleep 5` (or similar) as the readiness gate.

---

### API start command resolution

Priority:

1. Reuse the pattern already in `scripts/start.sh` (venv + editable installs + **uvicorn** entrypoint)
2. Existing documented npm/python command in repo docs / root scripts
3. Fail with instructions

Documented start (from `scripts/start.sh`) — do not invent alternatives:

```bash
# after: source .venv/bin/activate
# after: pip install -e packages/shared-python -e services/api
uvicorn pathline_api.main:app --host 127.0.0.1 --port "$API_PORT" --reload
```

**Do not invent** paths such as:

```bash
python services/api/main.py
python -m pathline_api
```

---

### 2. Environment compatibility

Reuse startup behavior from `scripts/start.sh`:

- `.venv` create/activate if missing
- `pip install -e packages/shared-python -e services/api`

Do **not** invent a second dependency installation flow.

Host bind must stay `127.0.0.1` (never `0.0.0.0` for desktop sidecar).

---

### 3. Process management

Create/use:

```
.logs/api-desktop.log
.pids/api-desktop.pid
```

When **this script** spawns the API:

- write spawned API PID to `.pids/api-desktop.pid`
- redirect stdout/stderr to `.logs/api-desktop.log`
- set ownership (`API_OWNED=1` and/or `.pids/api-desktop.owned` marker)

When reusing an already-healthy API:

- `API_OWNED=0`
- do not overwrite a foreign/alive PID as if owned

---

### 4. Shutdown handling

Trap: `EXIT` `INT` `TERM`

| Owned API? | On Ctrl+C / exit |
|------------|------------------|
| Yes (`API_OWNED=1`) | `kill` PID from `.pids/api-desktop.pid`, remove pid + ownership marker |
| No (reused) | **do not kill** |

**Do not `exec` Tauri** — keep the shell so traps can clean up an owned API.

Avoid orphaning the API **you** started; never kill a developer’s pre-existing API.

---

### 5. Desktop launch

After API health succeeds:

```bash
cd desktop
npm run dev
```

Desktop is the foreground child. When it exits or the operator hits Ctrl+C, owned API is stopped; a reused API is left alone.

Linux GTK/WebKit preflight may remain as a **read-only check** that prints remediation and exits — do not install system packages from this agent and do not expand ownership to `scripts/install-linux-tauri-deps.sh` unless explicitly asked.

---

## package.json

Ensure:

```json
{
  "scripts": {
    "desktop:dev": "./scripts/desktop-dev.sh"
  }
}
```

Do not rename existing scripts. `desktop:build` / `desktop:deps:linux` may remain if already present.

---

## Validation

Smoke where the environment allows:

```bash
npm run desktop:dev
```

Expected log shape (wording flexible):

```
[api] healthy on 127.0.0.1:8000   # or "reusing existing"
[desktop] launching tauri dev
```

---

## Completion Criteria

Agent is complete when:

- [ ] `npm run desktop:dev` starts API automatically when none is healthy
- [ ] Existing healthy API is reused without duplicate spawn
- [ ] Ctrl+C cleans **only** owned API
- [ ] API logs persist in `.logs/api-desktop.log`
- [ ] Health wait uses **250ms** poll / **30s** max (no fixed `sleep 5`)
- [ ] No forbidden files modified
- [ ] `git diff` contains only:
      - `scripts/desktop-dev.sh`
      - `package.json` (and only `desktop:*` script churn)

---

## Failure cases

| Failure | Expected |
|---------|----------|
| API cannot become healthy within 30s | Clear error + log path + PID if available |
| Port occupied, health fails | Detect conflict; fail without killing foreign PID |
| Missing venv tools | Explain remediation (`python3 -m venv`) |
| Missing desktop deps | Pass through `npm` error from `desktop/` |
| Ctrl+C | API cleanup **only if owned** |

---

## Output

Deliver only:

```
scripts/desktop-dev.sh
package.json   # desktop:dev (keep existing desktop:* if present)
```

No architecture changes. No Rust changes. No RunSession / API source / `client/**` changes.

This is a **Wave 1 infrastructure agent** — land before SIP/STT agents. Safe to run in parallel with U1/U2 as long as file ownership stays exclusive.
