# IVRSuite (IVR Assessor)

IVRSuite is a local-first, permissioned IVR route discovery, call-path mapping,
and suite execution system.

It is built for authorized testing of business-owned IVRs: operators can explore
unknown branches, run repeatable suites against known flows, and review bounded
run diagnostics afterward without changing the deterministic live call path.
Operator-facing guidance stays IVR-native: use route discovery, call-path
mapping, suite execution, and replay/review language.

---

## Core Features

- **Route Discovery:** A bounded depth-first search (DFS) loop for exploring unknown branches safely.
- **Call-Path Mapping:** Live operator views and persisted maps for prompts, options, and transitions.
- **Suite Execution:** Repeatable suites that use approved DTMF or speech response anchors against known flows.
- **Post-Run Review:** Runtime inspection and replay tools for analyzing chronology, checkpoint verification, and route refinement after a run.
- **TTS Response Audio:** Optional utility support for creating speech clips used as response audio during route checks.

## Operational Phases

1. **Suite Planning / Configuration** — define the target IVR, reusable inputs, route checks, and readiness bounds.
2. **Live Operations / Active Run** — supervise one bounded discovery or suite execution run.
3. **Review / Replay / Analysis** — inspect the resulting map, checkpoint verification, recordings, and bounded diagnostics.

See `backend/python/docs/OPERATIONS.md` for the operator workflow and terminology.
The canonical planning/governance anchor for product language is
`.ai/plans/ivr-phase-operations-anchor.md`.

---

## Prerequisites

1. **Python 3.11+**
2. **ngrok** (for tunneling the local streaming server)
3. Provider Accounts:
   - **Twilio** (Account SID, Auth Token, and an active Phone Number)
   - **Deepgram** (API Key for transcription)
   - **OpenAI** (Optional, for TTS response audio)

Create a `.env` file at the root of the repository with the following:

```env
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
DEEPGRAM_API_KEY=your_key

# Optional
USER_PHONE_NUMBER=+1098765432
OPENAI_API_KEY=your_key
```

---

## Quickstart

The primary entry point is the shell script launcher:

```bash
# Launch the Live Map GUI (Cockpit)
./run_ivr_assessor.sh live-map-gui
```

Navigate to `http://localhost:8080` in your browser. The tool will automatically attempt to start `ngrok` and bind to the correct streaming ports.

---

## CLI Command Reference

The Typer CLI offers several modes of operation for automated testing and CI/CD environments.

### 1. Automated Discovery Loop
Run an iterative mapping loop that uses DFS to find the deepest unexplored menu option. Stops automatically when no progress is made or when all announced options are walked.
```bash
./run_ivr_assessor.sh iterate-map --target-number +18005550199 --max-calls 12 --wall-clock-cap-s 30
```

### 2. Suite Execution
Run route checks where specific prompt matches trigger approved DTMF or speech response anchors.

**Create a suite interactively:**
```bash
./run_ivr_assessor.sh test-suite-wizard --output suites/my_test.json
```

**Run a suite:**
```bash
./run_ivr_assessor.sh test-suite --suite suites/my_test.json --output reports/
```
*(Note: You can also visually plan and execute reusable suites directly inside the Live Map GUI.)*

### 3. TTS Response Audio
Generate high-quality TTS audio clips to use as injected speech responses.
```bash
./run_ivr_assessor.sh voice-generate --text "Representative please" --out clips/response.wav --voice cedar
```

### 4. Utilities
- `map`: Run a single or multi-session map dynamically.
- `replay`: Reconstruct a mapped graph from a saved JSON trace.
- `dry-run`: Validate execution bounds and allowlist configuration without dialing.
- `sms-serve`: Run a local webhook server to bridge SMS replies into mapping jobs.

---
*For safety, the IVR Suite relies on an explicit allowlist architecture to prevent dialing unauthorized numbers.*
