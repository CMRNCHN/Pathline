# Pathline — Full AI Onboarding Context

> **Start here.** This document gives a new AI agent complete orientation on
> Pathline: what it is, where it is in development, what's actively being built,
> what's forbidden, and what to read before touching anything.
>
> Companion files: `AGENTS.md` (agent workflow + ownership), `.ai/HANDOFF.md`
> (session state), `.ai/ARCHITECTURE_RULES.md` (hard constraints).

---

## 1. What Pathline Is

Pathline is a **local-first, deterministic IVR assessment operating system**.
It makes real phone calls, listens to automated phone trees (IVRs), maps their
full menu structure, runs regression test suites against them, and produces a
verifiable audit record of every session.

**Target users:** QA engineers, telecom analysts, and product operators who need
to test and monitor IVR systems systematically without manual effort.

**Key differentiator:** Every session is fully replayable from an immutable
append-only event log. Replay is pure (`events → state`), deterministic, and
used as the single source of truth for analysis.

---

## 2. Architecture: Five Layers

Pathline enforces a **strict unidirectional dependency flow:**

```
Analyst → Governance → Replay → Runtime → Events
```

No layer may import from a layer downstream of it. Topology enforcement tests
in `tests/test_architecture.py` are authoritative and must never be weakened.

| Layer | Path | What it does |
|---|---|---|
| **Runtime** | `runtime/` | Deterministic execution kernel. Audio pipeline, STT/TTS, DFS discovery loop, event emission. No knowledge of governance or agents. |
| **Replay** | `replay/` | Pure temporal reconstruction. Consumes the event ledger → reconstructs state at any point. Never feeds back into live runtime. |
| **Governance** | `governance/` | Executable operational law: invariants, topology rules, agent contracts, design tokens. |
| **Analyst** | `analyst/` | Human-facing layer. Jinja-rendered GUI (server-side), FastAPI routes, operator console. Vanilla JS only, no build step. |
| **Agent** | `agents/` | Constrained AI helpers. Non-authoritative. Read-only access to replay artifacts. |

### Hard topology rules

- **Analyst → Runtime:** Analyst may never directly mutate runtime state. Must go through the API and EventBus.
- **AI → Replay:** Agents may annotate or summarize replays, never mutate event logs.
- **Replay → Runtime:** Replay is observational. Never feeds state back into a live session.
- **UI → Events:** Frontend never rewrites or deletes events from the append-only ledger.

---

## 3. Core Invariants (non-negotiable)

**Runtime invariants (R-001 through R-005):**
- R-001: Hot path is deterministic and bounded. No recursive AI. No autonomous LLM routing.
- R-002: All runtime processes have explicit bounds (max calls, wall-clock cap, depth limit).
- R-003: Route handlers are thin. Business logic belongs in domain modules.
- R-004: GUI on port 8080, streaming server on port 8081.
- R-005: Events are immutable once committed to the ledger.

**Replay invariants (RP-001 through RP-004):**
- RP-001: Replay is a pure function: `events → state`. No side effects.
- RP-002: Replay is the definitive record of what occurred.
- RP-003: Replay must reconstruct exact state at any point in the timeline.
- RP-004: Replay consumes events from the ledger. It does not feed control back into runtime.

**Architecture invariants:**
- No production imports from tests (ever).
- Events are append-only and never modified after commit.
- Topology enforcement tests are authoritative.
- Incremental migration only — no big-bang rewrites.

---

## 4. The Hot Path (DO NOT MODIFY without explicit justification)

```
Twilio μ-law audio
→ runtime/media/audio_pipeline.py   (μ-law decode → 16kHz PCM → RMS normalize → WebRTC VAD)
→ runtime/stt_service               (FasterWhisper local, confidence gate: exp(avg_logprob) ≥ 0.6)
→ transcript_filter.py              (dedup rolling 3-utterance window + short transcript gate)
→ runtime/discovery_loop.py         (deterministic DFS routing)
→ runtime/tts_service               (Piper local + 200-entry LRU cache → Twilio μ-law)
→ Twilio response
```

Runtime constraints (also DO NOT CHANGE without justification):
- VAD silence threshold: 15 frames = 300ms
- VAD max segment: 1500 frames = 30s
- Whisper confidence gate: `exp(avg_logprob) ≥ 0.6`
- Transcript dedup window: 3 utterances
- TTS LRU cache: 200 entries
- Package: `webrtcvad-wheels` (not `webrtcvad` — broken with setuptools 82+)

Cloud fallbacks are env-controlled (`STT_BACKEND=deepgram`, `TTS_BACKEND=openai`) and never default.

---

## 5. Server Topology

```
Single OS process
├── Port 8080: ThreadingHTTPServer  (analyst GUI — live_map_gui.py)
└── Port 8081: FastAPI/uvicorn      (StreamingServer — background thread)

Shared state:
- AppState (STATE) singleton
- RunSuiteState (RS_STATE) singleton
- EventBus: central pub/sub for OperationalEvent instances
- EventSink: subscribes to EventBus, persists to append-only JSONL
```

Storage layout: `~/.ivr_assessor/{events,recordings,replays,snapshots,suites,reports,benchmarks}/`

---

## 6. Current Phase: Enforcement Mode + Replay Inspection Productization Pass

### Phase: Enforcement Mode

Pathline completed its architectural redesign (layered domain separation,
frontend standardization, 330 passing tests). It is now in **Enforcement Mode**:
hardening layer boundaries, eliminating import violations, and freezing contracts.

Current enforcement priorities (from `.ai/NEXT_SESSION.md`):
1. Remove replay/runtime path leakage from analyst layer
2. Topology enforcement: reduce tolerated violations incrementally
3. Schema completeness: finalize frozen schemas in `schemas/`
4. Runtime/replay event contract freezing

Before any session: run `pytest tests/test_architecture.py -q` to confirm topology is clean.

### Active Pass: Replay Inspection Productization

**Feature branch:** `next/replay-and-runtime-usability`  
**Goal:** One canonical `ReplayInspectionReport` used identically by CLI, API, and UI.

This is a **productization pass, not an architecture pass.** Scope is strictly:
operator workflows for "what happened / where it failed / what changed / what to inspect next."

**Agent workflow (from AGENTS.md):**

| Batch | Agents | Status |
|---|---|---|
| Batch 1 (serial) | Agent 1: schema + service | D1 ✅ merged, D2 ✅ merged, D3 in progress, D4 in progress |
| Batch 2 (parallel) | Agents 2, 3, 4 | waiting for Agent 1 completion |
| Batch 3 (serial) | Agent 5: validation + docs | waiting for Agents 2–4 |

**Files already merged to feature branch:**
- `replay/inspection_models.py` — canonical `ReplayInspectionReport` schema with `schema_version="1.0"`, `Anomaly`, `NextStep`, `Reference` models
- `replay/bundle_resolver.py` — resolves artifacts (event log, snapshots, recordings, bookmarks, etc.) for a session id; reports partial availability explicitly

**Files owned by Agent 1, in progress:**
- `replay/inspection_service.py` — D3: orchestrates bundle resolution + report construction
- `replay/inspection.py` (shim) — D4: existing file becomes thin compat re-export

**Files to be created in Batch 2:**
- `replay/anomaly_detection.py` — Agent 3: `detect_anomalies` + `generate_next_steps`
- `replay/cli.py` (new `inspect` subcommand) — Agent 2
- `analyst/backend/routes/replay_routes.py` (new inspection route) — Agent 2
- `analyst/frontend/templates/replay_inspection.html` — Agent 4
- `analyst/frontend/static/js/replay_inspection.js` — Agent 4

**File to be created in Batch 3:**
- `docs/replay-inspection/` — Agent 5 (operator guide + developer contract)

**File ownership is hard.** No agent edits files outside their column. See AGENTS.md ownership table.

---

## 7. Known Issues

- `faster-whisper` streaming requires `webrtcvad-wheels` at runtime; degradation is clean when absent
- `audioop` deprecation warning on Python 3.12 (harmless; use `audioop-lts>=0.2.1` on 3.13)
- pytest collection warnings for `TestTrigger`, `TestCase` in `test_suite.py` — harmless
- Import boundary enforcement is still incomplete — topology violations tolerated but being reduced incrementally

---

## 8. What to Read First (for any agent)

Required reading before making any change:

1. **`AGENTS.md`** — workflow, file ownership, definition of done, pre-edit ritual, required output format
2. **`.ai/ARCHITECTURE_RULES.md`** — hard layer constraints
3. **`.ai/PROJECT_STATE.md`** — current stability status, what's known-good
4. **`governance/architecture/topology.md`** — authoritative layer dependency graph
5. **Your role's task doc** in `docs/agent-tasks/replay-inspection/<role>.md`

Then read every file you plan to modify or that your code will import from.

The **pre-edit ritual** (required for every agent, from AGENTS.md):
1. List every file you intend to read
2. Read them
3. List every file you intend to modify or create
4. Confirm none are outside your ownership column
5. Only then begin edits

---

## 9. What NOT to Do

- **No broad architecture rewrites** — this is a productization pass
- **No opportunistic renames or refactors** outside your owned files
- **No UI redesign** outside the replay inspection workflow (Agent 4's scope)
- **No test churn** — existing tests must pass without being deleted or weakened
- **No silent file deletions or moves** — every commit summary includes `Removed/Moved:` section
- **No changes to files outside your ownership column** — escalate instead
- **No production imports from tests**
- **No LLM routing in the hot path**
- **No React, webpack, Vite, or any build step** — vanilla JS only
- **Do not introduce `.air/` directory** — `.ai/` is the only continuity area
- **Do not reduce topology enforcement test coverage**

---

## 10. Repodock & Context Packaging

### RepoDock (`.ai/` folder)

The `.ai/` folder is the RepoDock — it persists session continuity across AI interactions:

```
.ai/
├── CONTEXT_FOR_AI.md      ← this file
├── HANDOFF.md             ← session-to-session state, last updated
├── PROJECT_STATE.md       ← stability milestones and test counts
├── NEXT_SESSION.md        ← pending work and priorities
├── ARCHITECTURE_RULES.md  ← hard layer constraints
├── DECISIONS/accepted/    ← architectural decision records
└── TASKS/COMPLETED/       ← completed task records
```

### Repomix context dump (for AI handoff)

To produce a complete file-content dump for AI ingestion:

```bash
repomix . --output .ai/repomix-output.txt --ignore-file .ai/.repomixignore
```

`.ai/repomix-output.txt` is gitignored. Review for secrets before sharing.

### Live tree

```bash
tree -I '__pycache__|.git|.venv*|node_modules|*.egg-info|.ruff_cache|.pytest_cache|.DS_Store' \
     --dirsfirst -a > TREE.md
```

---

## 11. Key Commands

```bash
# Environment setup
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run all tests
pytest tests/ -q
# Expected: ~330 passing

# Topology enforcement check (always run before making changes)
pytest tests/test_architecture.py -q

# Run replay tests only
pytest tests/test_inspection.py tests/test_replay_*.py -q

# Start the GUI
./scripts/run_ivr_assessor.sh live-map-gui
# → http://localhost:8080

# Docker stack
./scripts/run_ivr_assessor.sh docker-up

# IVR discovery run
./scripts/run_ivr_assessor.sh iterate-map --target-number +18005550199 --max-calls 12

# Repomix context dump
repomix . --output .ai/repomix-output.txt --ignore-file .ai/.repomixignore
```

---

## 12. Quick Reference: Key Files

| File | Why it matters |
|---|---|
| `AGENTS.md` | Agent workflow, file ownership, definition of done |
| `.ai/ARCHITECTURE_RULES.md` | Hard layer constraints (authoritative) |
| `governance/architecture/topology.md` | Layer dependency graph |
| `governance/runtime/runtime_invariants.md` | R-001 through R-005 |
| `governance/replay/replay_truth_model.md` | RP-001 through RP-004 |
| `replay/inspection_models.py` | Canonical report schema (do not modify outside Agent 1 ownership) |
| `replay/bundle_resolver.py` | Artifact resolver for inspection |
| `runtime/state/event_ledger.py` | Append-only event store (never mutate) |
| `tests/test_architecture.py` | Topology enforcement (never weaken) |
| `tests/test_inspection.py` | Pins inspection behavior (must pass unchanged through D4) |
| `analyst/backend/routes/replay_routes.py` | Replay API (Agent 2 adds inspect route) |
| `infrastructure/config/paths.py` | Canonical path constants |
| `docs/agent-tasks/replay-inspection/` | Per-agent task definitions for active pass |
