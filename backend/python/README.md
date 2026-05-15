# IVR Assessor — Developer Guide

## Setup (< 10 minutes)

### 1. Create Virtual Environment
```bash
cd backend/python
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Install Package
```bash
pip install -e ".[interactive]"
```

### 3. Run Tests
```bash
python -m pytest -q
# Expected: 306 passing tests
```

### 4. Launch GUI
```bash
# Set credentials in .env first (see /.env.example)
./../../run_ivr_assessor.sh live-map-gui
```

## Development Workflows

### Running Tests
```bash
# Quick test run
python -m pytest -q

# Single test file
python -m pytest tests/test_replay_sync.py -v

# Watch mode (requires pytest-watch)
ptw -- -q
```

### Common Development Tasks

**Adding a new CLI command:**
- Edit `src/ivr_assessor/cli.py`
- Add `@app.command()` function
- Test with `python -m ivr_assessor <command> --help`

**Modifying replay logic:**
- Core files: `src/ivr_assessor/events/replay_*.py`
- Tests: `tests/test_replay_*.py`
- Hot path preserved: deterministic state reconstruction, append-only events

**Adding a new route:**
- Edit `src/ivr_assessor/backend/routes/*.py`
- HTTP handling in `src/ivr_assessor/live_map_gui.py` (LiveMapRequestHandler)
- Frontend integration in `src/ivr_assessor/frontend/static/js/`

## Architecture Overview

**Single-process, local-first design:**
- Runtime supervisor monitors active sessions
- Event bus publishes OperationalEvents for all state changes
- Replay is deterministic: snapshot + event replay = exact state at any cursor position
- No external state backend; all replay-visible data is local

**Key Files:**
- `live_map_gui.py` — HTTP server, request routing, startup orchestration
- `runtime/` — Session monitoring, recovery, cleanup
- `events/` — Event models, replay reconstruction, snapshot management
- `frontend/static/js/` — UI modules (replay, timeline, state management)
- `backend/routes/` — API endpoint handlers

## Testing Strategy

- **306 tests** covering discovery, mapping, replay, event ledger, and suite execution
- **Deterministic replay tests** verify snapshot + event reconstruction
- **Smoke tests** validate CLI commands and HTTP routes
- Tests run in <4 seconds; focus is on correctness, not performance

## No Abstractions

The codebase intentionally avoids:
- Async/await for simplicity (single-process concurrency only)
- Frameworks beyond Typer (CLI) and FastAPI (future)
- Heavy type abstractions
- Dependency injection or plugin systems

This preserves explicit control flow and makes debugging straightforward.

---

**Questions?** See `docs/OPERATIONS.md` for operational workflows or `../../.ai/` for architecture notes.
