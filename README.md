# Pathline: Deterministic IVR Assessment OS

Pathline is a local-first, operator-guided IVR discovery and testing platform. It is designed as a deterministic operating environment with executable governance and clear operational layering.

## System Layers

- **Runtime Layer** (`runtime/`): Deterministic execution kernel, media pipelines, and transport.
- **Replay Layer** (`replay/`): Temporal truth reconstruction and synchronized media playback.
- **Governance Layer** (`governance/`): Operational law, invariants, and agent contracts.
- **Analyst Layer** (`analyst/`): Human interaction (GUI) and operational interpretation.
- **Agent Layer** (`agents/`): AI orchestration and assistant capability boundaries.

## Filesystem Structure

```text
/pathline
├── runtime/      — Deterministic execution kernel, media, transport, and state
├── replay/       — Temporal truth reconstruction, timelines, and media sync
├── governance/   — Operational law, invariants, and agent contracts
├── analyst/      — Human interaction layer (GUI, API routes, and UI state)
├── agents/       — AI orchestration, prompts, and capability boundaries
├── infrastructure/ — Config, Docker, and environment setup
├── tools/        — Benchmarks and utility scripts
├── tests/        — Regression suites and system tests
├── sessions/     — Operational continuity (active session state and logs)
├── evidence/     — Immutable artifacts, recordings, and manifests
├── docs/         — Educational concepts and walkthroughs
├── .ai/          — Operational governance, stability milestones, and handoffs
├── schemas/      — Machine-readable object validation
├── scripts/      — Operator shell entrypoints
└── README.md
```

## Quickstart

### Prerequisites

- Python 3.12+
- ngrok or Cloudflare Tunnel (for Twilio webhooks)
- Twilio account

### Local Launch

```bash
# 1. Setup the environment
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Start the GUI
./scripts/run_ivr_assessor.sh live-map-gui
# → opens http://localhost:8080
```

### Docker Launch

```bash
# Start the full stack (API + STT/TTS model pre-warmers)
./run_ivr_assessor.sh docker-up
```

## Documentation

- [**Operations Guide**](docs/OPERATIONS.md) — Detailed operator workflows (Prep, Discover, Call/Live, Run, Review).
- [**Developer Guide**](docs/DEVELOPER_GUIDE.md) — Backend architecture, testing, and contribution notes.
- [**Stability Milestone**](.ai/PROJECT_STATE.md) — M1 stability criteria and project status.
- [**Enforcement Priorities**](.ai/NEXT_SESSION.md) — Current priorities and deprioritizations.

## Safety & Security

- **Allowlist:** Pathline enforces an explicit allowlist of authorized phone numbers.
- **Local-First:** All session data, recordings, and event logs are stored locally in `~/.ivr_assessor/`.
- **Operator-in-the-loop:** Designed for supervised exploration, preventing autonomous dialing loops.

---
**Authoritative Layered Architecture (Enforcement Mode)**
