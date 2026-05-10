# IVRSuite — Active Handoff

Last Updated: 2026-05-10 (bounded replay inspection tooling)

---

## Current Status

Platform is in strong architectural shape with Air governance structure established.
251/251 backend tests passing.

### Completed this session (bounded replay/runtime inspection tooling)

- Added `backend/python/src/ivr_assessor/inspection.py` as a pure, additive inspection helper for:
  - replay artifact summaries
  - event chronology views
  - runtime timeline reconstruction
  - queue/checkpoint visibility summaries
  - websocket lifecycle rollups
  - operator-facing correlation payloads
- Added CLI utilities:
  - `ivr-assessor inspect-replay --trace-path ...`
  - `ivr-assessor inspect-runtime --metrics-path ...`
  - `ivr-assessor inspect-runtime --runtime-url http://127.0.0.1:8080/api/runtime-diagnostics`
- Expanded live GUI observability additively:
  - new `GET /api/runtime-diagnostics`
  - `GET /api/runtime-metrics` now includes bounded `last_session` inspection state
  - end-of-session snapshot preserves the last session’s bounded chronology for offline/operator inspection
- Preserved runtime/replay guarantees:
  - no hot-path audio/transcription/routing changes
  - no replay generation behavior changes
  - no websocket protocol changes
  - no topology/orchestration changes
- Validated with:
  - `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/test_inspection.py backend/python/tests/test_cli_smoke.py backend/python/tests/test_live_map_gui.py backend/python/tests/test_replay_mode.py backend/python/tests/test_streaming_server_auth.py -q -p no:cacheprovider`
  - Result: `34 passed`

### Completed this session (streaming/runtime stabilization)

- `streaming_server.py` no longer fails WebSocket auth/connect tests when `webrtcvad`
  is missing locally; VAD initialization now degrades cleanly instead of aborting the socket.
- `logging_config.py` now falls back to stdlib logging when `structlog` is unavailable,
  which restores CLI smoke commands in lean local environments.
- `transcript_filter.py` stats payload preserves the numeric-zero initial contract while
  still exposing `last_text` only after transcripts are seen.
- Validated with `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/ -q`
  → 246 passed.

### Completed this session (runtime/replay architecture mapping)

- Added `.ai/RUNTIME_REPLAY_ARCHITECTURE_MAP.md` as an operator-focused map of current startup ordering, runtime lifecycle, websocket chronology, replay visibility, cleanup sequencing, stale-runtime detection, and probe flow.
- Documented current-state contracts only: no topology changes, no websocket semantic changes, no replay semantic changes.
- Captured remaining blind spots explicitly, including the current gap between runtime metrics directory visibility and actual replay/snapshot artifact production.

### Completed this session (bounded transcript simulation slice)

- Added `STT_BACKEND=simulated` as a deterministic operational-validation backend for downstream transcript flow before local CT2 model provisioning.
- The simulated backend emits a fixed four-step transcript script on buffered media chunks:
  - short transcript drop
  - accepted transcript
  - deduplicated repeat
  - second accepted transcript
- Extracted the existing live-map transcript/status callback bridge into a small helper so the real prompt-queue path can be exercised without changing topology.
- Added one focused smoke test that validates:
  - transcript injection through the existing WebSocket stream loop
  - transcript filter counters and dedup behavior
  - websocket/status update cadence under media flow
  - queue/checkpoint visibility
  - runtime/replay visibility payload shape
  - callback teardown and cleanup sequencing
- Validated with:
  - `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/test_stt_service.py backend/python/tests/test_streaming_server_auth.py -q`
  - `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/ -q`
  - Result: `251 passed`

### Completed this session (bounded runtime observability hardening)

- Added lightweight runtime checkpoint preservation in `AppState`:
  - launch sequence counter
  - bounded checkpoint ring buffer
  - cleanup event tracking
  - deterministic reset accounting
- Added bounded prompt queue observability via `ObservableQueue`:
  - current depth
  - max depth seen
  - put/get counters
  - last enqueue/dequeue timestamps
- Expanded `/api/runtime-metrics` payload to expose:
  - runtime checkpoints
  - session prompt queue metrics
  - replay/snapshot/report directory summaries
  - stale-runtime detection payload
- Expanded `streaming_server.py` runtime metrics to expose:
  - websocket lifecycle chronology ring buffer
  - callback cleanup counters
  - disconnect reasons / close codes
  - media byte counters
  - buffer overflow counters
  - recording lifecycle chronology
- Deterministic smoke coverage added for:
  - websocket lifecycle + cleanup metrics
  - runtime checkpoint snapshot behavior
  - prompt queue metrics
- Validated with `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/ -q`
  → 248 passed.

### Completed this session (Air governance)

- `__pycache__` / `.pyc` cleaned (418 dirs, 4158 files removed)
- Stale `IVRSuite_ai_docs.zip` archive removed from repo root
- `.gitignore` updated: added `.ai_sessions/`, storage artifact patterns, `*.zip`
- `.ai/` governance structure normalized:
  - Added: `AIR_RULES.md`, `TASKS/`, `DECISIONS/`, `SESSION_LOGS/`
  - Removed: stale `AI_CONTEXT.md` (absorbed into `PROJECT_STATE.md`), empty `SESSION_LOG.md`
  - Updated: `PROJECT_STATE.md` (complete rewrite, current state)
- Domain boundary directories established in `ivr_assessor/`:
  - `runtime/`, `websocket/`, `routes/`, `ui/`, `storage/`, `config/`, `monitoring/`, `events/`
  - Each has stub `__init__.py` with purpose + migration status — no code moved
- `storage/` at repo root established: `replays/`, `reports/`, `benchmarks/`, `recordings/`, `snapshots/`

### Completed previous session (maintainability stabilization)

- `frontend/static/js/common/` layer: time, dom, api, events (+EventBus), state, websocket
- `main.js` and `run_suites.js` refactored to use `common/` layer
- `live_map_gui.py` split: `backend/ui/ui_state.py`, `template_loader.py`, `frontend_assets.py`,
  `backend/routes/mapper_routes.py`, `backend/routes/run_suite_routes.py`
- Test suite editor extracted: `main.js` → `frontend/static/js/modules/test_suites.js`
- Storage path constants centralized in `ui_state.py`
- `config/.env.example` created with all env vars documented
- `.ai/RUNTIME_SPLIT_POINTS.md` created

---

## AI Governance Files (load at session start)

```
.ai/
├── HANDOFF.md             — this file; session-to-session state
├── PROJECT_STATE.md       — current architecture, test count, storage paths, commands
├── ARCHITECTURE_RULES.md  — hard constraints on what is never allowed
├── AIR_RULES.md           — Air workflow protocol, refactor protocol, red flags
├── NEXT_SESSION.md        — pending work and priorities
├── RUNTIME_SPLIT_POINTS.md — what blocks a future process split
├── TASKS/                 — active task files (one per work item)
├── DECISIONS/             — architectural decision records
└── SESSION_LOGS/          — per-session logs
```

---

## Current Architecture

### Hot path (DO NOT modify without explicit approval)

```
Twilio μ-law audio
→ audio_pipeline.py  (decode → 16kHz PCM → normalize → WebRTC VAD)
→ stt_service.py     (FasterWhisper local, confidence gate >= 0.6)
→ transcript_filter.py (dedup rolling window + short transcript gate)
→ deterministic DFS routing (discovery_loop.py)
→ tts_service.py     (Piper local + LRU cache)
→ Twilio response
```

### Backend structure

```
ivr_assessor/
  backend/
    routes/
      mapper_routes.py       — mapper API handlers
      run_suite_routes.py    — run suite API handlers
    ui/
      ui_state.py            — AppState, RunSuiteState, QueuePromptSource + all storage paths
      template_loader.py     — HTML template rendering
      frontend_assets.py     — static file serving + path traversal protection
  live_map_gui.py            — thin HTTP dispatcher + session thread + launch()
  streaming_server.py        — WebSocket server (port 8081, FastAPI/uvicorn)
  run_suites/                — models, runner, loader, reports
  [domain boundary stubs]    — runtime/, websocket/, routes/, ui/, storage/, config/, monitoring/, events/
```

### Frontend structure

```text
frontend/static/js/
  common/            — time.js, dom.js, api.js, events.js (+EventBus), state.js, websocket.js
  modules/test_suites.js
  main.js, run_suites.js
```

---

## Hard Rules (do not re-ask)

| Decision                  | Answer                                              |
|---------------------------|-----------------------------------------------------|
| Frontend framework        | None — vanilla JS only                              |
| Build step                | None — no webpack, Vite, Rollup                     |
| Runtime LLM orchestration | Never                                               |
| Backend framework         | stdlib http.server — no FastAPI on the GUI side     |
| Hot path modifications    | None without explicit user approval                 |
| Abstraction depth         | Improve structure, never increase complexity        |
| Domain boundary migration | Document only — do NOT move code without instruction|

---

## Credentials to Rotate

All previously exposed credentials should be rotated:

- Twilio (TWILIO_AUTH_TOKEN)
- OpenAI (OPENAI_API_KEY)
- Deepgram (DEEPGRAM_API_KEY)
- AssemblyAI (ASSEMBLYAI_API_KEY)

---

## Next Priorities

See `.ai/NEXT_SESSION.md` for details.

1. Backend unified event bus (`events/event_bus.py`) — centralize callback dispatch
2. Session snapshots — end-of-run state capture to `storage/snapshots/`
3. WER benchmark smoke test with real audio fixture
4. Smoke test local pipeline (`STT_BACKEND=faster-whisper`, `TTS_BACKEND=piper`)

Operational note:
- Full local FasterWhisper media-flow validation remains blocked by external model provisioning.
- Runtime observability is now stronger at the pre-transcription boundary, including websocket,
  cleanup, artifact, and stale-runtime visibility.
