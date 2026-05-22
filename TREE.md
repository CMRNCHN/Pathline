# Pathline — Directory Tree

> Regenerate this file after structural changes:
> ```bash
> tree -I '__pycache__|.git|.venv*|node_modules|*.egg-info|.ruff_cache|.pytest_cache|.DS_Store|*.pyc|*.wav|*.mp3|*.onnx|*.bin' \
>      --dirsfirst -a \
>      > TREE.md
> ```
> Then edit the header back in. Or use repomix for a full file-content dump:
> ```bash
> repomix . --output .ai/repomix-output.txt --ignore-file .ai/.repomixignore
> ```

Last updated: 2026-05-22  
Branch: `next/replay-and-runtime-usability`

---

```
Pathline/
├── .ai/                                    ← RepoDock: session continuity (authoritative)
│   ├── ARCHITECTURE_RULES.md               ← hard layer constraints
│   ├── CONTEXT_FOR_AI.md                   ← full AI onboarding doc (start here)
│   ├── HANDOFF.md                          ← session-to-session state
│   ├── NEXT_SESSION.md                     ← pending priorities for next session
│   ├── PROJECT_STATE.md                    ← stability milestones, current status
│   ├── DECISIONS/
│   │   └── accepted/
│   │       ├── 2026-05-09-bounded-runtime-observability.md
│   │       ├── 2026-05-10-operator-console-modernization.md
│   │       └── 2026-05-10-transcript-simulation-backend.md
│   └── TASKS/
│       └── COMPLETED/
│           ├── 2026-05-14_frontend_refresh.md
│           ├── 2026-05-14-pathline-renaming.md
│           └── 2026-05-14-repodock-consolidation.md
│
├── analyst/                                ← human interaction layer
│   ├── __init__.py
│   ├── backend/
│   │   ├── routes/                         ← HTTP API handlers
│   │   └── ui/                             ← AppState, template loader, asset serving
│   ├── frontend/
│   │   ├── static/                         ← vanilla JS + CSS (no build step)
│   │   └── templates/                      ← Jinja server-rendered HTML
│   ├── phone_tracker_gui.py
│   ├── telecom/
│   └── ui/
│
├── docs/
│   ├── agent-tasks/
│   │   └── replay-inspection/              ← ACTIVE: per-agent task definitions
│   │       ├── README.md                   ← workflow order, status vocabulary, branch convention
│   │       ├── agent-1-schema.md           ← D1 merged, D2 merged, D3+D4 in progress
│   │       ├── agent-2-cli-api.md          ← ready (waiting for Agent 1)
│   │       ├── agent-3-anomalies.md        ← ready
│   │       ├── agent-4-ui.md               ← ready
│   │       └── agent-5-validation.md       ← waiting for Agents 2–4
│   ├── legacy/                             ← archived pre-migration docs
│   ├── superpowers/                        ← original design specs
│   ├── CHANGELOG.md
│   ├── DEVELOPER_GUIDE.md
│   ├── OPERATIONAL_COHESION_CHECKLIST.md
│   ├── OPERATIONS.md                       ← operator workflow guide
│   ├── REPLAY_WALKTHROUGH.md
│   ├── RUNTIME_SPLIT_POINTS.md
│   └── SYSTEM_CAPABILITIES.md
│
├── governance/                             ← executable operational law
│   ├── agents/
│   │   ├── agent_execution_contract.md
│   │   └── AGENTS.md
│   ├── architecture/
│   │   ├── event_model.md
│   │   └── topology.md                     ← layer dependency graph + forbidden mutations
│   ├── principles/
│   │   └── core_principles.md
│   ├── replay/
│   │   ├── replay_truth_model.md           ← RP-001 through RP-004
│   │   └── snapshot_semantics.md
│   ├── runtime/
│   │   └── runtime_invariants.md           ← R-001 through R-005
│   ├── security/
│   │   └── evidence_integrity.md
│   └── ui/
│       └── design_tokens.md
│
├── infrastructure/
│   ├── config/
│   ├── docker/
│   └── docker-compose.yml
│
├── replay/                                 ← temporal truth layer
│   ├── __init__.py
│   ├── bundle_resolver.py                  ← Agent 1 D2 ✅ artifact resolver
│   ├── cli.py                              ← replay CLI (Agent 2 adds inspect subcommand)
│   ├── inspection.py                       ← Agent 1 D4: becomes compat shim (in progress)
│   ├── inspection_models.py                ← Agent 1 D1 ✅ canonical schema
│   ├── inspection_service.py               ← Agent 1 D3 (in progress)
│   ├── media_sync/
│   ├── reducers/
│   ├── replay_mode.py
│   ├── reporting.py
│   ├── runtime_projection.py
│   ├── serialization/
│   ├── snapshots/
│   ├── timelines/
│   └── verification/
│
├── runtime/                                ← deterministic execution kernel
│   ├── __init__.py
│   ├── decisions.py
│   ├── discovery_loop.py                   ← DFS IVR mapping loop (HOT PATH)
│   ├── events/
│   │   ├── bookmark_service.py
│   │   ├── annotation_service.py
│   │   └── ...
│   ├── exploration.py
│   ├── ivr_mapper.py
│   ├── kernel/
│   ├── media/
│   ├── multi_session.py
│   ├── phone_tracker.py
│   ├── prompt_intelligence.py
│   ├── sessions/
│   ├── sms_server.py
│   ├── state/
│   │   ├── event_ledger.py                 ← append-only event persistence
│   │   ├── replay_state.py
│   │   └── ...
│   ├── supervision/
│   ├── telemetry/
│   ├── telephony.py
│   ├── transport/
│   └── twilio_client.py
│
├── schemas/
│   ├── decision.schema.json
│   ├── event.schema.json
│   └── session_state.schema.json
│
├── scripts/
│   ├── probe_runtime.sh
│   └── run_ivr_assessor.sh
│
├── sessions/
│   └── active/
│
├── storage/
│   └── reports/
│
├── tests/                                  ← 330 passing, 1 skipped (2026-05-22)
│   ├── fixtures/
│   ├── run_suites/
│   ├── test_bundle_resolver.py
│   ├── test_inspection.py
│   ├── test_inspection_models.py
│   ├── test_replay_*.py                    ← 15+ replay test files
│   └── [80+ total test files]
│
├── tools/
│   ├── __init__.py
│   ├── benchmarks/
│   └── pathline_cli.py
│
├── AGENTS.md                               ← source of truth: agent workflow + file ownership
├── CLAUDE.md                               ← instructs Claude to read AGENTS.md
├── README.md
├── TREE.md                                 ← this file
└── pyproject.toml
```

---

## Key path annotations

| Path | Role |
|---|---|
| `.ai/` | RepoDock — session continuity, never deleted |
| `replay/inspection_models.py` | Canonical report schema, owned exclusively by Agent 1 |
| `runtime/state/event_ledger.py` | Append-only event store — never mutated |
| `analyst/backend/routes/replay_routes.py` | Replay API routes (Agent 2 adds inspect route) |
| `governance/architecture/topology.md` | Authoritative layer dependency graph |
| `tests/test_architecture.py` | Topology enforcement tests — never weaken |
| `docs/agent-tasks/replay-inspection/` | Active pass task docs — delete when pass complete |
