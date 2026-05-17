# RepoDock — Pathline Operational Continuity

RepoDock is the living repository continuity system for Pathline. It provides a deterministic checkpoint for engineering state, project memory, and operational context.

## Read Order

1. `README.md` (this file) — entrypoint and philosophy.
2. `CURRENT/PROJECT_STATE.md` — technical status and test count.
3. `CURRENT/ACTIVE_PRIORITIES.md` — what we are doing right now.
4. `ARCHITECTURE/ARCHITECTURAL_INVARIANTS.md` — core rules that must not be broken.

## Operational Philosophy

- **Local-First**: All core logic, storage, and processing must be capable of running entirely on the operator's machine.
- **Deterministic Replay**: If the same events are played back, the system state should reconstruct identically.
- **Single Source of Truth**: Continuity files in `.ai/REPODOCK` represent the verified state of the project.
- **Append-only Lineage**: We maintain a clear history of changes and decisions.

## Architectural Invariants

- **Single Process**: The GUI server and runtime currently live in one process.
- **Bounded Behavior**: No infinite loops, recursive agents, or uncontrolled resource usage.
- **Explicit Control Flow**: Avoid complex abstractions; favor direct callables and thin route handlers.
- **Deterministic DFS**: IVR discovery follows a reproducible depth-first search.

## Non-Goals

- **Distributed Orchestration**: No K8s, microservices, or complex cloud-native architectures.
- **Frontend Frameworks**: No React/Vue/Svelte; stick to vanilla JS for simplicity.
- **Autonomous LLM Agents**: No hidden orchestration or agentic loops in the hot path.
- **Generic Automation**: This is a specialized tool for IVR assessment, not a general-purpose RPA platform.

## Operator Quick-Start

- **Start GUI**: `./run_ivr_assessor.sh live-map-gui`
- **Start Discovery**: `./run_ivr_assessor.sh iterate-map --target-number <NUMBER> --max-calls 12`
- **Run Tests**: `pytest backend/python/tests/ -q`

## Structure

- **CURRENT/**: System pulse, active priorities, and latest stable checkpoint.
- **ARCHITECTURE/**: Runtime maps, split points, and invariant rules.
- **HANDOFFS/**: Active handoff state and historical session logs.
- **TASKS/**: Active objectives and completed task records.
- **LOGS/**: Append-only changelog of repository evolution.
- **PLANS/**: Strategic execution plans and agent lanes.
- **CONTEXT/**: Repomix snapshots and repository context for LLM agents.
