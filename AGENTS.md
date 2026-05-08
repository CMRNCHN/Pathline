# Repository Guidelines

## Project Purpose

IVRSuite is a local-first, permissioned IVR assessment tool. It maps phone-tree IVRs, runs scripted regression suites, supports live GUI mapping, and performs audio QA benchmarking.

## Session Protocol

At the start of any engineering session, read these files first:

1. `.ai/PROJECT_STATE.md` — current architecture, test status, known issues, commands.
2. `.ai/ARCHITECTURE_RULES.md` — hard runtime/backend/frontend constraints.
3. `.ai/NEXT_SESSION.md` — current priorities and explicit non-goals.
4. `.ai/HANDOFF.md` — latest handoff details, if present and relevant.

At the end of meaningful code changes:

1. Run the most relevant tests, preferably `pytest backend/python/tests/ -q` from the repo root when practical.
2. Summarize changed boundaries, risks, and validation performed.
3. Update `.ai/HANDOFF.md` when architectural behavior or session state changes.
4. Update `.ai/NEXT_SESSION.md` only if priorities shifted.
5. Record non-obvious architectural decisions under `.ai/DECISIONS/`.

## Core Commands

- Install backend dev dependencies: `cd backend/python && python -m venv .venv && .venv/bin/pip install -e ".[dev]"`
- Run tests from repo root: `pytest backend/python/tests/ -q`
- Known local pyenv test command: `/Users/cameroncohen/.pyenv/versions/3.12.8/bin/pytest backend/python/tests/ -q`
- Launch GUI: `./run_ivr_assessor.sh live-map-gui`
- Launch discovery loop: `./run_ivr_assessor.sh iterate-map --target-number +18005550199 --max-calls 12`

## Architecture Constraints

Preserve deterministic, bounded, replayable, low-latency behavior in the runtime hot path:

```text
Twilio μ-law audio
→ audio_pipeline.py
→ stt_service.py
→ transcript_filter.py
→ deterministic DFS routing
→ tts_service.py
→ Twilio response
```

Do not modify hot-path behavior unless explicitly asked and the change is scoped, tested, and justified.

Runtime must not contain:

- Recursive AI agents.
- LangChain, LlamaIndex, CrewAI, or LLM orchestration frameworks.
- Autonomous LLM routing.
- Giant context windows or uncontrolled async reasoning.
- Hidden side effects.

## Backend Guidelines

- Keep route handlers thin; business logic belongs in `backend/python/src/ivr_assessor/backend/routes/` or existing domain modules.
- Keep UI/shared state in `backend/python/src/ivr_assessor/backend/ui/ui_state.py`.
- Keep WebSocket streaming semantics in `backend/python/src/ivr_assessor/streaming_server.py`.
- Do not change the WebSocket protocol or token auth scheme without explicit instruction.
- Do not break `STATE` / `RS_STATE` singleton patterns without a full plan.
- Do not add FastAPI to the GUI server path or introduce async GUI framework changes unless explicitly requested.
- Prefer `ValueError` and `FileNotFoundError` for domain errors in route handlers.
- Add storage path constants to `ui_state.py` instead of scattering path literals.

## Frontend Guidelines

- Use lightweight vanilla JavaScript only.
- Do not add React, Next.js, Vue, Svelte, Redux, MobX, Zustand, Vite, webpack, Rollup, or any frontend build step.
- Keep frontend behavior explicit and debuggable; avoid hidden reactivity or state machines.
- Use the existing `frontend/static/js/common/` layer for shared frontend utilities.

## Refactor Rules

For refactors, follow this sequence:

1. Define exact scope and touched boundaries.
2. Make the smallest coherent change.
3. Run targeted tests, then broader tests when practical.
4. Verify no import errors or changed public contracts.
5. Summarize boundaries changed, risks introduced, and future pressure.

For large refactors touching more than three files or crossing domain boundaries, ask for confirmation before starting.

Do not do these without explicit instruction:

- Move code between modules.
- Rename public API endpoints.
- Modify `streaming_server.py` internals.
- Add new dependencies to `pyproject.toml`.
- Create new Python packages in the main path.
- Redesign architecture or migrate code into future target domains.
- Commit or push changes.

Stop and ask before adding abstraction-heavy constructs such as base classes, protocol layers, plugin systems, hook systems, configuration DSLs, decorators that alter control flow, or dependency injection containers.

## Testing Notes

The expected baseline from `.ai/PROJECT_STATE.md` is 240 passing tests, with one known environment-sensitive failure: `test_stream_websocket_accepts_valid_token` may fail when `webrtcvad` is unavailable in the active Python environment.

Do not replace `webrtcvad-wheels` with `webrtcvad`; the latter is known to break with newer setuptools versions.

## Secrets and Safety

- Never commit real secrets or credentials.
- Treat `.env` files as sensitive.
- Use `.env.example` files for documenting required variables.
- The tool is for authorized IVR testing only; preserve allowlist and safety controls.
- Do not weaken dialing, authorization, webhook token, or replay safety checks.

## Style Preferences

- Prefer small, explicit functions and low abstraction depth.
- Prefer direct callables over shared global state for new coordination points.
- Keep changes surgical and consistent with existing code.
- Avoid hidden dispatch, dynamic resolution, or side effects in hot paths.
- Do not add inline comments unless they explain non-obvious behavior.
