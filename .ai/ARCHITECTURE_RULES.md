# ARCHITECTURE RULES

## Domain Ownership

runtime/
- execution
- state transitions
- event processing

replay/
- temporal reconstruction
- replay reducers
- replay verification

analyst/
- operator UX
- reporting
- visualization

agents/
- constrained AI helpers only

tests/
- validation only
- never imported by production

## Hard Constraints

- no production imports from tests
- deterministic replay required
- append-only event model preserved
- topology enforcement tests authoritative
- incremental migration only

## Workspace bootstrap policy

`.ai/` is the only repository-managed AI/session continuity area.
Do not introduce or regenerate `.air/`.
Any tool or assistant operating in this repository must treat `AGENTS.md` and `.ai/*` continuity files as authoritative.
