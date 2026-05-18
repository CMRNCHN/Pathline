# Agent Execution Contract

## A-001: Authority Hierarchy
- AI Agents are assistants, not primary authorities.
- Every architectural change requires human-readable justification and confirmation for large scopes (>3 files).

## A-002: Action Scoping
### Allowed Actions
- Annotate and classify sessions.
- Summarize transcripts.
- Fix failing tests and import errors.
- Improve inline documentation.
- Add storage path constants.

### Forbidden Actions
- Mutate runtime core logic without explicit instruction.
- Rewrite historical event logs.
- Add new frontend frameworks or build steps.
- Introduce LLM orchestration frameworks (LangChain, etc.).
- Bypass or weaken safety controls (allowlist, rate limits).

## A-003: Operational Protocol
- AI must load `PROJECT_STATE.md`, `/governance/runtime/runtime_invariants.md`, and `/sessions/handoffs/` at start.
- AI must run tests after any meaningful code change.
- AI must update `/sessions/handoffs/` at session end.

## A-004: Abstraction Guardrails
AI must stop and ask before adding:
- Base classes or metaclasses.
- New protocol/interface layers.
- Message queues between directly calling modules.
- Plugin or hook systems.
- Configuration DSLs.
- Dependency injection containers.
