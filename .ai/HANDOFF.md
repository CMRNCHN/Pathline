# AI HANDOFF — IVRSuite
_Last updated: 2026-05-06_

## Current Goal
Ship a complete, polished IVR phone-tree mapper with test-suite runner.

## Current State
- **105 tests passing, 0 failing** (`cd backend/python && .venv/bin/python -m pytest -q`)
- Active branch: `main`
- GUI runs at `http://localhost:8080` via `./run_ivr_assessor.sh live-map-gui`
- ngrok tunnel: `inequilateral-consolidative-anja.ngrok-free.dev` → port 8081
- All credentials in `.env` at repo root (gitignored)

## What Changed Recently (this session)
1. `streaming_server.py` — stream auth token now hashed from Twilio creds (deterministic, survives restarts)
2. `live_map_gui.py` — auto-pilot toggle, startup credential check, Deepgram key check in `_diagnose()`
3. `live_map_gui.py` — test suite GUI: 3-column variable table, pipe-delimited data loader, default 28-column schema
4. `test_suite.py` — `TestTrigger.title` field; `variables` dict with `$varname` interpolation
5. `twilio_client.py` — caller ID rotation via `TWILIO_PHONE_NUMBERS` pool (10 numbers)
6. `transcription.py` — IVR keyword boosts (account number, CVV, zip code, etc.) wired into Deepgram connect
7. `audio_quality.py` — NEW: `LocalWhisperTranscriber` (free, implemented); paid stubs for AssemblyAI, Twilio Voice Intelligence, Dolby
8. `.env.example` — documents all vars incl. new `DEEPGRAM_KEYWORDS`, `ASSEMBLYAI_API_KEY`, `DOLBY_API_KEY`, `TWILIO_INTELLIGENCE_SERVICE_SID`

## Decisions Made (do not re-ask)
| Question | Answer |
|---|---|
| Redesign layout | Cockpit (A) — 320px right rail |
| DTMF detection | Strict: `/^[\s0-9*#]+$/` only |
| Discovery loop strategy | DFS — deepest unexplored option |
| Stopping condition | 2 consecutive no-progress calls |
| Test format | JSON ground truth + CLI runner (`test-suite` command) |
| Auto-pilot toggle location | Top of rail, above smart input |
| Flow editor / presets | Removed — test_suite.py supersedes them |
| Stream auth | Hash of TWILIO_ACCOUNT_SID:TWILIO_AUTH_TOKEN (not random); or `IVR_STREAM_AUTH_TOKEN` env var |
| Test suite data intake | Pipe-delimited schema row + data row (28 columns); `$varname` interpolation in responses |
| Audio quality (free) | Deepgram keywords + LocalWhisperTranscriber; paid services are stubs |
| TTS default voice | `cedar` (OpenAI); override with `OPENAI_TTS_VOICE` env var |

## Open Questions
- None blocking. Paid audio quality integrations (AssemblyAI, Dolby, Twilio Intelligence) are stubbed in `audio_quality.py` — activate when budget allows.

## Next Actions
1. Try a live call end-to-end — run `./run_ivr_assessor.sh live-map-gui` and test transcription
2. Wire `LocalWhisperTranscriber` to post-process call recordings when they arrive via `/recording-status` webhook
3. Move Swift files out of `backend/python/src/ivr_assessor/` (misplaced; tracked as deleted in git status)

## Files To Check First
- `backend/python/src/ivr_assessor/live_map_gui.py` — GUI + all API endpoints
- `backend/python/src/ivr_assessor/streaming_server.py` — Twilio WS + Deepgram bridge
- `backend/python/src/ivr_assessor/transcription.py` — Deepgram transcriber with keyword boosts
- `backend/python/src/ivr_assessor/audio_quality.py` — Whisper + paid stubs
- `backend/python/src/ivr_assessor/test_suite.py` — batch test runner
- `backend/python/src/ivr_assessor/cli.py` — all commands inc. `test-suite`, `iterate-map`
- `backend/python/tests/` — 105 tests, all passing

## Rules For Future AI
- Read this file first. Update it before ending work.
- Do not duplicate logic — the old `flow` system is gone; `test_suite.py` is the replacement.
- Preserve all existing JS hooks in `live_map_gui.py` (`poll`, `padPress`, `sendInput`, etc.)
- `test_suite.py` dataclasses are named `Test*` — pytest warns about collection; harmless.
- Always run `cd backend/python && .venv/bin/python -m pytest -q` before committing.
- `.env` is gitignored but `.env.example` (at both repo root and `backend/python/`) documents all vars.
