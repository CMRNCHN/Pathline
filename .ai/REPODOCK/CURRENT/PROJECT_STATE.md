# IVRSuite — Project State

Last Updated: 2026-05-14

---

## Purpose

Local-first telecom automation platform: maps phone-tree IVRs automatically
(calls, listens, presses keys, builds a visual menu graph), runs scripted
regression suites against IVR systems, and supports audio QA benchmarking.

---

## Test Suite

**317 passing**

```bash
/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/ -q
```

---

## Replay & Media Infrastructure (Slice 11: Playback Engine)

- **ReplayState & ReplayCursor**: Deterministic reconstruction model with playback state and rate synchronization.
- **MediaReplayService**: Resolves session recordings and provides media/cursor/alignment lookups.
- **WaveformService**: Generates and retrieves RMS/peak bucket metadata from PCM audio recordings.
- **ReplayService & ReplayLoader**: Supports seeking and nearest-event lookups for temporal navigation.
- **Frontend Playback**: `replay_audio.js` (HTML5 Audio wrapper) and `replay_waveform.js` (Canvas renderer) integrated with `ReplayTimeline`.
- **Mode Isolation**: Playback strictly read-only; `exitReplay()` ensures all media stops.

---

## Event Infrastructure (Slice 3: Persistence)

- **EventBus**: Central pub/sub for `OperationalEvent` instances.
- **EventSink**: Subscribes to `EventBus` and persists all events to append-only JSONL files.
- **Storage Layout**: `~/.ivr_assessor/events/YYYY-MM-DD/session_<session_id>.jsonl`.
- **ReplayLoader**: Utility for reconstructing timelines from persisted event streams.
- **Lineage**: Initial `session_id` propagation through `StreamingServer` and `EventBus`.

---

## Hot Path (DO NOT MODIFY)

```
Twilio μ-law audio
→ audio_pipeline.py  (μ-law decode → 16kHz PCM → RMS normalize → WebRTC VAD)
→ stt_service.py     (FasterWhisper local, confidence gate exp(avg_logprob) >= 0.6)
→ transcript_filter.py (dedup rolling 3-utterance window + short transcript gate)
→ deterministic DFS routing (discovery_loop.py)
→ tts_service.py     (Piper local + 200-entry LRU cache → Twilio μ-law)
→ Twilio response
```

Cloud fallbacks (env-controlled, not in default hot path):

- `STT_BACKEND=deepgram` → DeepgramTranscriber
- `TTS_BACKEND=openai` → OpenAITTS

Operational validation path (env-controlled, not in default hot path):

- `STT_BACKEND=simulated` → deterministic transcript script for downstream runtime/media-flow validation

---

## Server Topology (single OS process)

- Port 8080: `ThreadingHTTPServer` (live_map_gui.py `launch()`)
- Port 8081: FastAPI/uvicorn StreamingServer (background thread)
- Shared state: `AppState` (STATE) and `RunSuiteState` (RS_STATE) singletons
- GUI polls `/api/status` every 500ms — no push channel yet
- Operational metrics now also expose:
  - startup event chronology
  - bounded runtime checkpoint chronology
  - websocket lifecycle chronology
  - prompt queue depth / max depth / put-get counters
  - cleanup counters and stale-runtime detection

See `.ai/RUNTIME_SPLIT_POINTS.md` for what blocks a process split.

---

## Backend Structure

```
backend/python/src/ivr_assessor/
├── backend/
│   ├── routes/
│   │   ├── mapper_routes.py      — mapper API handlers
│   │   └── run_suite_routes.py   — run suite API handlers
│   └── ui/
│       ├── ui_state.py           — AppState, RunSuiteState, QueuePromptSource + storage paths
│       ├── template_loader.py    — HTML template rendering
│       └── frontend_assets.py    — static file serving + path traversal protection
├── live_map_gui.py               — thin HTTP dispatcher + session thread + launch()
├── streaming_server.py           — WebSocket server (port 8081)
└── run_suites/                   — models, runner, loader, reports
```

## Frontend Structure

```
frontend/static/js/
├── common/           — time.js, dom.js, api.js, events.js (+ EventBus), state.js, websocket.js
├── modules/
│   └── test_suites.js
├── main.js
└── run_suites.js
```

---

## Domain Boundaries (future migration targets — DO NOT MIGRATE YET)

```
ivr_assessor/
├── runtime/       — session thread, DFS loop, execution controller
├── websocket/     — streaming_server, audio pipeline
├── routes/        — HTTP API handlers (currently in backend/routes/)
├── ui/            — state singletons, template/asset serving (currently in backend/ui/)
├── storage/       — file I/O: maps, replays, snapshots, reports
├── config/        — env loading, validation
├── monitoring/    — logging, ledger, benchmarks
└── events/        — EventBus, event constants, future typed events
```

---

## Storage Paths (runtime, all in ~/.ivr_assessor/)

All constants live in `backend/ui/ui_state.py`:

| Constant                | Path                               |
|-------------------------|------------------------------------|
| SUITES_DIR              | ~/.ivr_assessor/suites/            |
| RUN_SUITES_DIR          | ~/.ivr_assessor/run_suites/        |
| REPORTS_DIR             | ~/.ivr_assessor/reports/           |
| RUN_SUITE_REPORTS_DIR   | ~/.ivr_assessor/run_suite_reports/ |
| RECORDINGS_DIR          | ~/.ivr_assessor/recordings/        |
| REPLAYS_DIR             | ~/.ivr_assessor/replays/           |
| SNAPSHOTS_DIR           | ~/.ivr_assessor/snapshots/         |
| BENCHMARKS_DIR          | ~/.ivr_assessor/benchmarks/        |
| EVENTS_DIR              | ~/.ivr_assessor/events/            |
| TEST_RUNS_DIR          | ~/.ivr_assessor/test_runs/         |

---

## Telecom Validation (Slice 8)

- **TelecomTestPlan**: Model for controlled real IVR tests (bounds, goals).
- **TelecomTestRunner**: Executes bounded tests, enforces limits, emits events.
- **SafetyGuards**: Real-time monitoring for duration, depth, DTMF, transfer, and confidence.
- **TelecomTestResult**: Structured outcome with failure/stop reasons.
- **EvidenceManifest**: JSON manifest linking event logs, replays, and snapshots.
- **API**: `/api/telecom-tests` (list), `/api/telecom-tests/run` (start), `/api/telecom-tests/<id>/status`, `/api/telecom-tests/<id>/evidence`.
- **Frontend**: "Controlled Operational Validation" panel in Prep workspace.

---

## Known Issues

- Faster-whisper streaming still requires `webrtcvad-wheels` at runtime; when absent,
  the stream server now degrades cleanly instead of failing WebSocket auth/connect flows.
- `audioop` deprecation warning on Python 3.12 (harmless; use `audioop-lts>=0.2.1` on 3.13)
- pytest collection warnings for `TestTrigger`, `TestCase` in `test_suite.py` — harmless

---

## Runtime Constraints (DO NOT CHANGE without justification)

- VAD silence threshold: 15 frames = 300ms
- VAD max segment: 1500 frames = 30s
- Whisper confidence gate: exp(avg_logprob) >= 0.6
- Transcript dedup window: 3 utterances
- TTS LRU cache: 200 entries
- webrtcvad package: `webrtcvad-wheels` (not `webrtcvad` — broken with setuptools 82+)

---

## Key Commands

```bash
# Install
cd backend/python && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Tests
/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/ -q

# GUI
./run_ivr_assessor.sh live-map-gui          # http://localhost:8080

# Discovery loop
./run_ivr_assessor.sh iterate-map --target-number +18005550199 --max-calls 12
```

---

## Tooling Notes

### Repomix (context dump for AI handoff)

```bash
repomix . --output .ai/repomix-output.txt --ignore-file .ai/.repomixignore
```

Review output for secrets before sharing. `.ai/repomix-output.txt` is gitignored.
