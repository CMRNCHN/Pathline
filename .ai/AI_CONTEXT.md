# AI CONTEXT — IVRSuite

## Project Purpose
Maps phone-tree IVRs automatically: calls a number, listens, presses keys, and builds a visual graph of the menu structure.

## Architecture
```
backend/python/
├── src/ivr_assessor/
│   ├── cli.py                # Typer CLI — all commands
│   ├── live_map_gui.py       # ~1200 LOC: Python HTTP server + full HTML/CSS/JS GUI
│   ├── live_map.py           # LiveMappingSession (wall_clock_cap_s, forced_branches)
│   ├── ivr_mapper.py         # IvrMapper + PromptNode + announced_options
│   ├── discovery_loop.py     # DFS planner + run_discovery_loop
│   ├── multi_session.py      # MultiSessionOrchestrator + combined_graph
│   ├── streaming_server.py   # WebSocket Twilio media stream <-> Deepgram bridge
│   ├── test_suite.py         # Batch test runner (TestTrigger, TestCase, etc.)
│   ├── prompt_intelligence.py
│   ├── exploration.py
│   └── scenario_runner.py
├── tests/                    # 88 tests, all passing
└── pyproject.toml
```

## Important Commands
```bash
# Install
cd backend/python && python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# Test
cd backend/python && .venv/bin/python -m pytest -q

# Run GUI
./run_ivr_assessor.sh live-map-gui          # opens http://localhost:8080

# Discovery loop
./run_ivr_assessor.sh iterate-map --target-number +18005550199 --max-calls 12

# Test suite (CLI)
./run_ivr_assessor.sh test-suite --suite example_test_suite.json
```

## Key Files
- `live_map_gui.py` — everything the user sees; all `/api/*` endpoints live here
- `streaming_server.py` — token auth, Twilio WS, Deepgram forwarding
- `test_suite.py` — TestTrigger / TestCase / run_test_suite_from_file
- `example_test_suite.json` — sample test suite at repo root

## Known Issues
- **Stream auth**: Twilio connects but stream server rejects as unauthorized. Token may go stale. See `streaming_server.py:default_stream_auth_token`.
- **Swift files misplaced**: `ContentView.swift` etc. are inside `backend/python/src/ivr_assessor/` — wrong location.
- **pytest collection warnings**: `TestTrigger`, `TestCase` etc. in `test_suite.py` trigger "cannot collect" warnings. Harmless.

## Conventions
- DTMF detection: `/^[\s0-9*#]+$/` (JS) — digits, `*`, `#` only
- Prompt normalization: collapse whitespace, strip trailing punctuation, lowercase
- GUI API endpoints: all `/api/` prefix, handled by `LiveMapRequestHandler`
- Default OpenAI TTS voice: `cedar` (env override: `OPENAI_TTS_VOICE`)
- Branch sort: numeric via `_branch_sort_key` (1, 2, 10 — not 1, 10, 2)
