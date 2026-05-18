# Pathline — Project State

Last Updated: 2026-05-18
Completion: 55% (Architectural Redesign Complete)

---

## Purpose

Pathline is a local-first, deterministic operating system for IVR assessment. It maps menu graphs, executes regression suites, and performs audio QA through a strictly layered architectural model.

---

## Test Suite

**318 passing**

```bash
.venv/bin/pytest tests/ -q
```

---

## Architectural Layers

- **Runtime Layer** (`runtime/`): Isolated deterministic execution kernel.
- **Replay Layer** (`replay/`): Authoritative temporal truth reconstruction.
- **Governance Layer** (`governance/`): Executable operational law and invariants.
- **Analyst Layer** (`analyst/`): Human interpretation layer and UI.
- **Agent Layer** (`agents/`): Constrained orchestration layer (non-authoritative).

---

## PATHLINE_M1_STABLE (Stability Milestone)

The following criteria must be maintained for M1 stability:

- **Deterministic Replay:** Verified stable truth reconstruction from event logs.
- **Import Graph:** Strictly enforced boundaries between layers; no circular dependencies.
- **Runtime Kernel:** Boundaries frozen; all external I/O isolated via transport layer.
- **Replay Purity:** No side effects during timeline reconstruction.
- **Event Schemas:** Frozen machine-readable schemas for all core events.
- **Topology Rules:** Enforced layer hierarchy (Analyst → Governance → Replay → Runtime).
- **Session Reconstruction:** Deterministic recovery of session state from immutable event logs.
- **Evidence Manifests:** Validated checksums and metadata for all session artifacts.

---

## Storage Layout (~/.ivr_assessor/)

All paths are canonically managed in `infrastructure/config/paths.py`.

| Constant                | Path                               |
|-------------------------|------------------------------------|
| SUITES_DIR              | ~/.ivr_assessor/suites/            |
| RUN_SUITES_DIR          | ~/.ivr_assessor/run_suites/        |
| REPORTS_DIR             | ~/.ivr_assessor/reports/           |
| RECORDINGS_DIR          | ~/.ivr_assessor/recordings/        |
| REPLAYS_DIR             | ~/.ivr_assessor/replays/           |
| SNAPSHOTS_DIR           | ~/.ivr_assessor/snapshots/         |
| EVENTS_DIR              | ~/.ivr_assessor/events/            |
| ANNOTATIONS_DIR         | ~/.ivr_assessor/annotations/       |

---

## Governance

- **Invariants:** `governance/runtime/runtime_invariants.md`
- **Contracts:** `governance/agents/agent_execution_contract.md`
- **Schemas:** `/schemas/` (event, session_state, decision)

---

## Known Issues

- `audioop` deprecation warning on Python 3.12 (harmless).
- One environment-sensitive test skipped (VAD requirement).

---

## Key Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

# Run GUI
./scripts/run_ivr_assessor.sh live-map-gui
```
