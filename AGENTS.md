# Repository Guidelines

## Purpose

Pathline is a local-first, deterministic IVR assessment system. The repository is organized around five authoritative layers:

- `runtime/` — deterministic execution kernel, media, sessions, transport
- `replay/` — temporal truth reconstruction, timelines, snapshots, verification
- `governance/` — operational law, invariants, topology, security rules
- `analyst/` — operator-facing backend routes, UI state, frontend assets
- `agents/` — constrained assistant capabilities; never authoritative runtime logic

## Start-of-Session Protocol

Read these files before making non-trivial changes:

1. `.ai/PROJECT_STATE.md`
2. `.ai/ARCHITECTURE_RULES.md`
3. `.ai/NEXT_SESSION.md`
4. `.ai/HANDOFF.md` when the current state or recent direction matters

Use `README.md` for the high-level system map. Use `governance/agents/AGENTS.md` and `governance/agents/agent_execution_contract.md` when work touches governance or agent-specific operating rules.

## Core Commands

- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
- Full test suite: `.venv/bin/pytest tests/ -q`
- Launch GUI: `./scripts/run_ivr_assessor.sh live-map-gui`
- Probe runtime: `./scripts/probe_runtime.sh`

## Architecture Constraints

Preserve these repo-level rules:

- Keep the hot path deterministic, bounded, replayable, low-latency, observable, and testable.
- Do not add recursive agents, autonomous LLM routing, LangChain-style orchestration, uncontrolled async reasoning, or hidden side effects.
- Replay is authoritative for truth reconstruction; runtime events are append-only.
- Respect the domain flow: Analyst -> Governance -> Replay -> Runtime.
- Do not create new architectural abstractions unless the existing structure clearly cannot hold the change.

## Backend and Domain Rules

- Keep HTTP route handlers thin in `analyst/backend/routes/`; push business logic into the appropriate domain module.
- Keep UI/shared state in `analyst/backend/ui/ui_state.py`.
- Keep WebSocket and transport behavior in `runtime/transport/`.
- Use `infrastructure/config/paths.py` for storage path constants instead of scattering filesystem literals.
- Prefer explicit `ValueError` and `FileNotFoundError` handling for operator-facing contract failures.
- Do not break public replay/runtime contracts without updating tests and the related operator docs.

## Frontend Rules

- Use lightweight vanilla JavaScript only.
- Do not add React, Vue, Svelte, Redux, MobX, Zustand, Vite, webpack, Rollup, or any frontend build step.
- Keep frontend behavior explicit, deterministic, and easy to debug.
- Reuse `analyst/frontend/static/js/common/` for shared browser utilities.

## Refactor Rules

For any change larger than a trivial fix:

1. Define the exact scope and the boundaries being touched.
2. Make the smallest coherent change that satisfies the request.
3. Run targeted tests first, then broader validation when practical.
4. Verify imports and public contracts still hold.
5. Summarize changed boundaries, validation, and residual risk.

Ask before doing any of the following unless the user explicitly requested it:

- moving code across top-level layers
- renaming public endpoints or core modules
- changing `runtime/transport/streaming_server.py` behavior
- adding dependencies
- introducing new framework-level abstractions or plugin systems
- committing or pushing

## Testing and Documentation

- Current expected baseline from `.ai/PROJECT_STATE.md`: `318 passing`
- Run the narrowest relevant tests for the touched area, then expand when risk justifies it.
- When behavior or priorities change, update the matching `.ai` continuity files:
  - `.ai/HANDOFF.md` for changed session state or architectural behavior
  - `.ai/NEXT_SESSION.md` for changed priorities
  - `.ai/DECISIONS/` for non-obvious architectural decisions

## Safety

- Never weaken allowlist, authorization, webhook, replay-safety, or evidence-integrity controls.
- Never commit real credentials or secrets.
- Treat `.env` files and anything under `~/.ivr_assessor/` as sensitive operator data.

## Workspace instruction source of truth

This repository does not use `.air/`.

Authoritative guidance lives in:
1. `AGENTS.md`
2. `.ai/PROJECT_STATE.md`
3. `.ai/ARCHITECTURE_RULES.md`
4. `.ai/NEXT_SESSION.md`
5. `.ai/HANDOFF.md` when present

Do not create, recreate, or rely on `.air/` bootstrap, settings, session, or context files.
If workspace bootstrapping is needed, read the `.ai/` files above as the sole source of truth.
