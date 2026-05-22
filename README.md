# Pathline: Deterministic IVR Assessment OS

Pathline is a **local-first, operator-guided IVR discovery and testing platform**. It operates as a deterministic execution environment with executable governance, clear operational layering, and a full replay/audit system.

**Current phase:** Enforcement Mode + Replay Inspection Productization Pass  
**Active branch:** `next/replay-and-runtime-usability`  
**Test suite:** 330 passing, 1 skipped

---

## What Pathline Does

- **Automatically maps IVR phone trees** — makes real calls, listens, presses keys, builds a live visual graph of all discovered menu states
- **Runs scripted regression test suites** against IVR systems with deterministic QA scoring
- **Deterministic session replay** — reconstructs any session frame-accurately from its append-only event log, with synchronized audio and waveform visualization
- **Evidence packaging** — cryptographically verifiable bundles of recordings, transcripts, and event logs for every session
- **Audio QA benchmarking** — integrated WER scoring for STT engine evaluation

---

## System Layers

| Layer | Path | Responsibility |
|---|---|---|
| **Runtime** | `runtime/` | Deterministic execution kernel, media pipelines, transport, session state |
| **Replay** | `replay/` | Temporal truth reconstruction, timeline management, synchronized media |
| **Governance** | `governance/` | Executable operational law, invariants, and agent contracts |
| **Analyst** | `analyst/` | Human interaction layer — GUI, API routes, UI state |
| **Agent** | `agents/` | Constrained AI orchestration (non-authoritative) |

Dependency flow: **Analyst → Governance → Replay → Runtime → Events**. No upstream layer may depend on a downstream layer.

---

## Filesystem Structure

```
pathline/
├── runtime/        — Deterministic execution kernel, media, transport, state
├── replay/         — Temporal truth reconstruction, timelines, media sync
│   ├── inspection_models.py      — canonical ReplayInspectionReport schema (D1 ✅)
│   ├── bundle_resolver.py        — artifact resolver for inspection (D2 ✅)
│   ├── inspection_service.py     — inspection orchestration (D3 in progress)
│   └── inspection.py             — compat shim (D4 in progress)
├── governance/     — Operational law, invariants, agent contracts
├── analyst/        — Human interaction layer (GUI, API routes, UI state)
├── agents/         — AI orchestration, prompts, capability boundaries
├── infrastructure/ — Config, Docker, and environment setup
├── tools/          — Benchmarks and utility scripts
├── tests/          — 330+ tests covering all subsystems
├── sessions/       — Active session state and operational logs
├── storage/        — Reports (recordings and replays are in ~/.ivr_assessor/)
├── schemas/        — Machine-readable event and state validation (JSON Schema)
├── scripts/        — Operator shell entrypoints
├── docs/           — Operations guide, developer guide, architecture walkthroughs
│   └── agent-tasks/replay-inspection/  — Per-agent task definitions (active pass)
├── .ai/            — Session continuity: handoff, state, decisions, tasks (RepoDock)
├── AGENTS.md       — Source of truth for agent workflow and ownership rules
└── TREE.md         — Live directory tree (see regeneration command inside)
```

---

## Quickstart

### Prerequisites

- Python 3.12+
- ngrok or Cloudflare Tunnel (for Twilio webhooks)
- Twilio account (for live calls)

### Local Launch

```bash
# 1. Set up environment
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Start the GUI
./scripts/run_ivr_assessor.sh live-map-gui
# → http://localhost:8080
```

### Docker Launch

```bash
# Full stack (API + STT/TTS model pre-warmers)
./scripts/run_ivr_assessor.sh docker-up
```

### Run Tests

```bash
pytest tests/ -q
# Expected: ~330 passing
```

---

## Operator Workflow

Five phases: **Prep → Discover → Call/Live → Run → Review**

1. **Prep** — configure target number, define DTMF/speech triggers, set safety bounds
2. **Discover** — bounded DFS: explores one unknown IVR branch per call, builds live graph
3. **Call/Live** — interactive session with live transcripts and operator console
4. **Run** — execute scripted test suites with automation health monitoring
5. **Review** — load a recorded session, scrub the timeline, inspect events and media

Full workflow details: [docs/OPERATIONS.md](docs/OPERATIONS.md)

---

## Active Work: Replay Inspection Productization Pass

**Branch:** `next/replay-and-runtime-usability`  
**Goal:** Make replay inspection a first-class operator workflow with one canonical `ReplayInspectionReport` used identically by CLI, API, and UI.

| Agent | Role | Status |
|---|---|---|
| Agent 1 | Schema + service | D1 merged, D2 merged, D3 running, D4 running |
| Agent 2 | CLI + API integration | ready (waiting for Agent 1 completion) |
| Agent 3 | Anomaly detection + next steps | ready |
| Agent 4 | Analyst UI workflow | ready |
| Agent 5 | Validation + docs (merge gate) | waiting for Agents 2–4 |

Task definitions: [docs/agent-tasks/replay-inspection/](docs/agent-tasks/replay-inspection/)  
Workflow rules and file ownership: [AGENTS.md](AGENTS.md)

---

## Architecture Hard Rules

- **Replay is the only authoritative source of truth** for what happened in a session
- **Runtime has no knowledge of governance or agents**
- **Events are append-only** — never modified after commit
- **Frontend framework: none** — vanilla JS only, no build step
- **No LLM routing in the runtime hot path** — strictly forbidden
- **No production imports from tests**
- **Topology enforcement tests are authoritative** — do not weaken them

Full governance rules: [.ai/ARCHITECTURE_RULES.md](.ai/ARCHITECTURE_RULES.md) and [governance/](governance/)

---

## Hot Path (DO NOT MODIFY without justification)

```
Twilio μ-law audio
→ audio_pipeline.py  (μ-law decode → 16kHz PCM → RMS normalize → WebRTC VAD)
→ stt_service.py     (FasterWhisper local, confidence ≥ 0.6)
→ transcript_filter.py (dedup rolling 3-utterance window)
→ discovery_loop.py  (deterministic DFS routing)
→ tts_service.py     (Piper local + 200-entry LRU cache → μ-law)
→ Twilio response
```

Cloud fallbacks are env-controlled and never default.

---

## Documentation

| Document | Purpose |
|---|---|
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Operator workflows (Prep → Review) |
| [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) | Backend architecture, testing, contribution |
| [docs/SYSTEM_CAPABILITIES.md](docs/SYSTEM_CAPABILITIES.md) | Full system capability reference |
| [docs/REPLAY_WALKTHROUGH.md](docs/REPLAY_WALKTHROUGH.md) | Replay system deep dive |
| [docs/RUNTIME_SPLIT_POINTS.md](docs/RUNTIME_SPLIT_POINTS.md) | What blocks a process split |
| [.ai/HANDOFF.md](.ai/HANDOFF.md) | Session-to-session state handoff |
| [.ai/PROJECT_STATE.md](.ai/PROJECT_STATE.md) | Stability criteria and current status |
| [.ai/CONTEXT_FOR_AI.md](.ai/CONTEXT_FOR_AI.md) | Full AI onboarding — start here for new agents |
| [AGENTS.md](AGENTS.md) | Agent workflow, ownership rules, definition of done |

---

## Safety

- **Allowlist** — only authorized phone numbers may be dialed; enforced at runtime
- **Local-first** — all session data, recordings, and event logs stored in `~/.ivr_assessor/`
- **Operator-in-the-loop** — no autonomous dialing loops; human approves each batch
- **Bounded execution** — max calls, wall-clock cap, and depth limits enforced at kernel level
