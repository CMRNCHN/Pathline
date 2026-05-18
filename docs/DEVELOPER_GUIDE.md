# Pathline — Developer Guide

## Setup (< 5 minutes)

### 1. Create Virtual Environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Install Package
```bash
pip install -e ".[dev]"
```

### 3. Run Tests
```bash
pytest tests/ -q
# Expected: ~318 passing tests
```

### 4. Launch GUI
```bash
./scripts/run_ivr_assessor.sh live-map-gui
```

## Development Workflows

### Running Tests
```bash
# Quick test run
pytest tests/ -q

# Single test file
pytest tests/runtime/test_session.py -v
```

### Common Development Tasks

**Adding a new API route:**
- Edit `analyst/backend/routes/`
- Register the route in the dispatcher

**Modifying replay logic:**
- Core files: `replay/` (reducers, serialization, timelines)
- Replay is the authoritative source of truth. Ensure all state changes are reflected in events.

**Updating the UI:**
- Templates: `analyst/frontend/templates/`
- Static Assets: `analyst/frontend/static/` (vanilla JS/CSS only)

## Architecture Overview (Enforcement Mode)

Pathline follows a strict layered architectural model:

1. **Runtime Layer** (`runtime/`): Isolated deterministic execution kernel. No knowledge of governance or agents.
2. **Replay Layer** (`replay/`): Authoritative temporal truth reconstruction. Pure and side-effect free.
3. **Governance Layer** (`governance/`): Executable operational law and invariants.
4. **Analyst Layer** (`analyst/`): Human interpretation layer (GUI, API routes).
5. **Agent Layer** (`agents/`): Constrained orchestration layer (non-authoritative).

### Key Constraints
- **Isolation**: Layers must only communicate through defined boundaries (Analyst → Governance → Replay → Runtime).
- **Immutability**: All events in the event log are append-only.
- **Local-First**: No external cloud state dependencies.

## Testing Strategy

- **Deterministic Replay Tests**: Verify that state can be perfectly reconstructed from event logs.
- **Boundary Tests**: Ensure layer isolation is maintained.
- **Hot Path Tests**: Validate the media pipeline and DFS routing.

## No-Complexity Principle

The codebase intentionally avoids:
- Frontend frameworks (No React/Vue/etc.)
- Build steps (No Webpack/Vite/etc.)
- Heavy abstractions or speculative "future-proofing".

This ensures that the system remains debuggable, transparent, and deterministic.
