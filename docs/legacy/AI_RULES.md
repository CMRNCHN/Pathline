# AI_RULES — Pathline AI-Assisted Development

Operational rules for AI-assisted development.
Read this file before any engineering session.

> **Planning artifacts are not implementation authorization.**

---

## Session Protocol

### At Session Start — Always Load

1. `.ai/PROJECT_STATE.md` — current architecture, test count, known issues
2. `.ai/ARCHITECTURE_RULES.md` — hard constraints, what is off-limits
3. `.ai/NEXT_SESSION.md` — pending work and priorities

### At Session End — Always Do

1. Run the full test suite and confirm no regressions
2. Update `.ai/HANDOFF.md` with:
   - What changed
   - Which domain boundaries were touched
   - Risks introduced
   - Future refactor pressure identified
3. Update `.ai/NEXT_SESSION.md` if priorities shifted
4. Log any non-obvious architectural decisions in `.ai/DECISIONS/`

---

## Always

- Preserve deterministic runtime behavior
- Preserve replayability — every call can be replayed from ledger
- Preserve WebSocket semantics in streaming_server.py
- Preserve existing tests — 240 passing is the floor, never the ceiling
- Preserve bounded queues in the hot path
- Preserve explicit routing — no hidden dispatch or dynamic resolution
- Preserve low abstraction depth — the next engineer must be able to read it cold
- Run tests after every meaningful refactor
- Summarize changed boundaries and introduced risks after any refactor

## Never

- Add React, Next.js, Vue, Svelte, or any frontend framework
- Add Redux, MobX, Zustand, or any state management library
- Add LangChain, LlamaIndex, CrewAI, or any LLM orchestration framework
- Add recursive AI agent systems to the runtime
- Add autonomous LLM routing to the hot path
- Add giant context windows or uncontrolled async reasoning
- Add hidden side effects to the hot path
- Redesign architecture without explicit user instruction
- Increase abstraction depth unnecessarily
- Introduce a new abstraction layer to solve a one-off problem
- Skip tests after a refactor
- Add a build step to the frontend (no webpack, Vite, Rollup, etc.)

## Prefer

- Incremental commits with scoped changes
- Explicit ownership — every function has a clear home
- Small modular improvements over large rewrites
- Passing callables rather than sharing global state across new modules
- ValueError / FileNotFoundError for domain errors in route handlers
- Vanilla JS with the existing `common/` layer for frontend work
- Adding constants to `ui_state.py` rather than scattering paths across modules

---

## What AI May Do Without Explicit Instruction

- Fix failing tests
- Fix import errors introduced by refactors
- Clean `__pycache__` and `.pyc` files
- Update `.ai/HANDOFF.md` and `.ai/NEXT_SESSION.md` at session end
- Add storage path constants to `ui_state.py`
- Improve inline documentation for non-obvious logic
- Add `.gitkeep` files to establish directory structure

## What AI Must NOT Do Without Explicit Instruction

- Move code between modules (even if it "belongs" there)
- Change the hot path in any way
- Add new dependencies to `pyproject.toml`
- Modify `streaming_server.py` internals
- Change the WebSocket protocol or token auth scheme
- Rename public API endpoints
- Create new Python packages (directories with `__init__.py`) in the main path
- Commit or push to the repository

---

## Domain Boundaries Reference

| Directory            | Owner Domain                          | Status        |
|----------------------|---------------------------------------|---------------|
| `backend/routes/`    | HTTP API handlers                     | Active        |
| `backend/ui/`        | State singletons, templates, assets   | Active        |
| `run_suites/`        | Run suite models, runner, reports     | Active        |
| `frontend/static/js/common/` | Frontend infrastructure       | Active        |
| `runtime/`           | Session thread, DFS, execution ctrl   | Future target |
| `websocket/`         | StreamingServer, audio pipeline       | Future target |
| `storage/`           | File I/O: maps, replays, reports      | Future target |
| `config/`            | Env loading, validation               | Future target |
| `monitoring/`        | Logging, ledger, benchmarks           | Future target |
| `events/`            | EventBus, typed event constants       | Future target |

"Future target" means: the boundary is established and documented.
Do NOT migrate code to future targets without explicit instruction.

---

## Protected Systems (Do not modify core logic)

- Replay chronology and semantics
- Deterministic traversal logic
- Inspection diagnostics
- Route verification
- Checkpoint semantics
- Bounded execution
- Protocol boundaries and topology

---

## Commit Discipline

Separate changes into distinct commits for:
- Governance/documentation
- Frontend UX
- Runtime/backend
- Replay semantics
- Storage changes

---

## Refactor Protocol

All refactors must follow this sequence:

1. **Scope** — define the exact files and boundaries being changed
2. **Modify** — make the change
3. **Test** — run `pytest backend/python/tests/ -q`
4. **Verify** — confirm no regressions, check for import errors
5. **Summarize** — note changed boundaries, introduced risks, future pressure
6. **Update** — update `HANDOFF.md` if anything architectural changed

For large refactors (touching >3 files or crossing domain boundaries):

- Get explicit confirmation before starting
- Break into independently-testable increments
- Commit each increment separately

---

## Most Important Principle

> **The system's greatest strength is LOW ABSTRACTION DEPTH + DETERMINISTIC ARCHITECTURE.**
>
> Improve structure WITHOUT increasing conceptual complexity.
> A future engineer reading this code should find it *simpler*, not more abstract.

---

## Red Flags (stop and ask the user)

If you find yourself about to:

- Add a new base class or metaclass
- Add a new protocol/interface layer
- Add a message queue between two modules that currently call each other directly
- Add a plugin or hook system
- Add a configuration DSL
- Add a decorator that changes control flow
- Add a dependency injection container

...stop and explicitly confirm with the user. These are abstraction escalations.
