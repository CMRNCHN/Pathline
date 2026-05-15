# RepoDock — IVRSuite / Pathline

RepoDock is the living repository continuity system for IVRSuite. It provides a deterministic checkpoint for engineering state, project memory, and operational context.

## Structure

- **CURRENT/**: System pulse, active priorities, and latest stable checkpoint.
- **ARCHITECTURE/**: Runtime maps, split points, and invariant rules.
- **HANDOFFS/**: Active handoff state and historical session logs.
- **TASKS/**: Active objectives and completed task records.
- **LOGS/**: Append-only changelog of repository evolution.
- **PLANS/**: Strategic execution plans and agent lanes.
- **CONTEXT/**: Repomix snapshots and repository context for LLM agents.

## Principles

- **Deterministic project memory**
- **Lean and operational**
- **Append-only operational lineage**
- **Single source of truth for repository state**

Updated after every completed task.
