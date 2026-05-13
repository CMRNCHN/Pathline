# IVRSuite — Active Handoff

Last Updated: 2026-05-13 (Slice 2: Real-Time Operational Telemetry Bridge)

---

## Current Status

Completed Slice 2 of Operational Cohesion phase. Established a real-time WebSocket telemetry bridge between the backend event bus and the frontend workspaces.

### Completed this session (Slice 2: Real-Time Operational Telemetry Bridge)

- **Backend WebSocket Bridge**:
    - Added `/ws/events` endpoint to `streaming_server.py`.
    - Integrated `StreamingServer` with the backend `EventBus` to broadcast `OperationalEvent` payloads.
    - Implemented safe subscriber management and cleanup for WebSocket clients.
- **Frontend Telemetry Client**:
    - Refined `WsManager` in `common/websocket.js` to automatically dispatch received events to the frontend `EventBus`.
    - Added reconnection logic and improved error handling for telemetry WebSockets.
- **Workspace Integration & Debug Visibility**:
    - Initialized the telemetry bridge in `main.js`, connecting to port 8081.
    - Added an "Operational Telemetry" tab to the Review drawer in `index.html`.
    - Implemented `renderTelemetryMonitor` in `main.js` to provide a real-time event log for developers.
    - Updated `renderDrawer` to explicitly handle the new telemetry workspace.
- **Validation**:
    - `pytest backend/python/tests/test_live_map_gui.py` (16 passed).
    - Verified real-time propagation of `CALL_STARTED`, `TRANSCRIPT_FINAL`, and other operational events.

## Remaining Operational Cohesion Gaps

- **Persistence**: Events are currently transient; need a lightweight sink to `storage/events/` for replay and auditability.
- **Lineage Tracking**: Fully wiring `session_id`, `state_id`, and `path_id` across all event sources.
- **Automated Escalation Visibility**: Routing `RUN_ESCALATED` events from the `Run` workspace to the `Live` workspace for immediate human intervention.

## Recommendations for Next Slice

- **Slice 3: Lightweight Event Persistence & Lineage Sink**: Implement a background worker to persist the `EventBus` stream to `storage/events/` in JSONL format, ensuring every operational event is recorded for forensic replay.

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
