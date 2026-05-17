# IVRSuite — Active Handoff
Last Updated: 2026-05-15 (Local usability push)

---

## Current Status

Completed replay workspace/data contract polish across frontend review rendering, replay routes, runtime cleanup/recovery semantics, deterministic replay media playback, waveform metadata generation, WER benchmark smoke coverage, and local readiness diagnostics.

### Completed this session

- Replaced mock review rendering with replay-backed header, timeline, transcript, bookmark, and template surfaces.
- Added replay route coverage for cursor, waveform, and alignment endpoints with explicit 400/404 behavior.
- Hardened startup/export/status payloads and made cleanup idempotent after registry removal.
- Updated operator and engineering docs to point at the real replay/demo flows.
- Added `/api/replays/<id>/media` for locally resolved WAV playback and wired the review audio player to replay cursor media offsets.
- Added deterministic on-demand waveform peak/RMS generation for local WAV recordings.
- Added WER benchmark smoke tests without requiring real Whisper model execution.
- Fixed readiness diagnostics so local-only/simulated mode no longer displays a working backend as broken.

## Remaining Operational Cohesion Gaps

- **Real-call readiness**: local GUI/replay/simulated STT mode is usable, but real outbound calls still require Twilio credentials, a public stream tunnel, and TTS provisioning.
- **Recovery policy depth**: operator guidance is explicit, but policy tiers/backoff are still open.

## Recommendations for Next Slice

- Provision real-call credentials and TTS assets, then run a controlled end-to-end call smoke.

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

1. Replay media playback tied to deterministic cursor movement
2. Waveform persistence instead of fallback-only metadata
3. WER benchmark smoke test with real audio fixture
4. Smoke test local pipeline (`STT_BACKEND=faster-whisper`, `TTS_BACKEND=piper`)

Operational note:
- Full local FasterWhisper media-flow validation remains blocked by external model provisioning.
- Runtime observability is now stronger at the pre-transcription boundary, including websocket,
  cleanup, artifact, and stale-runtime visibility.
