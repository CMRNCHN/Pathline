# Pathline (IVR Assessor)

IVRSuite is a local-first, operator-guided IVR discovery and testing platform. It enables authorized exploration of unknown call flows, execution of repeatable test suites, and deterministic replay of recorded sessions.

## What It Does

- **Route Discovery:** Bounded depth-first exploration of unknown IVR branches
- **Call-Path Mapping:** Live operator view of prompts, options, and transitions
- **Test Suites:** Repeatable DTMF/speech-response checks against known flows
- **Post-Run Review:** Deterministic replay and analysis of recorded sessions

## Three Phases

1. **Plan** — Define target IVR, inputs, routes, and bounds
2. **Run** — Execute discovery or suite with live operator supervision
3. **Review** — Replay session, refine map, export results

## Quickstart

**Prerequisites:** Python 3.11+, ngrok, Twilio, Deepgram accounts. See `.env.example` for setup.

```bash
# Launch the interactive GUI
./run_ivr_assessor.sh live-map-gui
# → opens http://localhost:8080
```

For CLI workflows, testing, and development:
- See [`backend/python/README.md`](backend/python/README.md) for developer setup
- See [`backend/python/docs/OPERATIONS.md`](backend/python/docs/OPERATIONS.md) for operator workflows

**Safety Note:** IVRSuite enforces an explicit allowlist to prevent unauthorized dialing.
