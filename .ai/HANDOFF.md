# IVRSuite — Active Handoff
Last Updated: 2026-05-13 (Slice 8: Real Telecom Test Harness & Operational Validation)

---

## Current Status

Completed Slice 8 of Operational Cohesion phase. Implemented a controlled, safe telecom validation harness for real-world IVR testing.

### Completed this session (Slice 8: Real Telecom Test Harness & Operational Validation)

- **Telecom Test Harness**:
    - Created `testing/telecom_test_plan.py` for bounded test configuration.
    - Created `testing/telecom_test_runner.py` to execute bounded tests and enforce safety limits.
    - Created `testing/safety_guards.py` for real-time monitoring of duration, depth, DTMF, transfer, and confidence.
    - Created `testing/evidence_manifest.py` for generating and retrieving JSON evidence manifests.
- **Persistence & API**:
    - Centralized `TEST_RUNS_DIR` in `backend/ui/ui_state.py`.
    - Implemented API routes for listing tests, starting tests, polling status, and retrieving evidence.
    - Fixed core logic bugs in Slice 8 stubs (imports, EventBus singleton usage, NameErrors).
- **Frontend**:
    - Integrated "Controlled Operational Validation" panel into the Prep workspace.
    - Added real-time polling and outcome visualization for telecom tests.
- **Validation**:
    - Added `tests/test_telecom_test_plan.py`, `test_safety_guards.py`, `test_evidence_manifest.py`, and `test_telecom_test_runner.py`.
    - Total passing tests: 296.

## Remaining Operational Cohesion Gaps

- **Scrubber UI**: Graphical scrubber for the operational timeline.
- **Synchronized Media Replay**: Linking the operational timeline to audio/waveform playback.
- **Autonomous Runtime Policies**: Advanced recovery strategies and automatic chaos mitigation.

## Recommendations for Next Slice

- **Slice 8: Visual Timeline Scrubber & Media Synchronization**: Implement the graphical scrubber and integrate audio playback synchronized with the operational cursor.

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
      replay_routes.py      — replay API handlers
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
  modules/
    test_suites.js
    replay.js
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
