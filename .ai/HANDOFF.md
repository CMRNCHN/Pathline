# AI HANDOFF — IVRSuite
_Last updated: 2026-05-02_

## Current Goal
Ship a complete, polished IVR phone-tree mapper with test-suite runner.

## Current State
- **88 tests passing, 0 failing** (`cd backend/python && .venv/bin/python -m pytest -q`)
- 3 commits on `main`: baseline → voice fix → auto-pilot toggle
- GUI runs at `http://localhost:8080` via `./run_ivr_assessor.sh live-map-gui`

## What Changed Recently
1. `ai_voice.py` — default voice → `cedar`; added compliance phrasing for PII/long-digit content
2. `live_map_gui.py` — auto-pilot toggle added to top of Cockpit rail (hits `/api/set-mode`)
3. `live_map_gui.py` — status payload now returns `manual_mode` so toggle syncs from server

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

## Open Questions
- **Stream auth bug**: Twilio connects but stream server rejects with "unauthorized". Suspected cause: stale token in GUI's saved stream URL. See `streaming_server.py` → `default_stream_auth_token` / `append_stream_auth_token`. Has a passing test (`test_streaming_server_auth.py`) but root cause unverified against live Twilio.

## Next Actions
1. Investigate stream auth bug (`streaming_server.py` token lifecycle)
2. Expose test-suite in GUI (spec: "Test Suite tab in left sidebar")
3. Move Swift files out of `backend/python/src/ivr_assessor/` (misplaced)

## Files To Check First
- `backend/python/src/ivr_assessor/live_map_gui.py` — GUI + all API endpoints
- `backend/python/src/ivr_assessor/streaming_server.py` — Twilio WS + Deepgram bridge
- `backend/python/src/ivr_assessor/test_suite.py` — batch test runner
- `backend/python/src/ivr_assessor/cli.py` — all commands inc. `test-suite`, `iterate-map`
- `backend/python/tests/` — 88 tests, all passing

## Rules For Future AI
- Read this file first. Update it before ending work.
- Do not duplicate logic — the old `flow` system is gone; `test_suite.py` is the replacement.
- Preserve all existing JS hooks in `live_map_gui.py` (`poll`, `padPress`, `sendInput`, etc.)
- `test_suite.py` dataclasses are named `Test*` — pytest warns about collection; harmless.
- Always run `cd backend/python && .venv/bin/python -m pytest -q` before committing.
