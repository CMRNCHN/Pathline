# IVR Suite (IVR Assessor)

A local, authorized tool for exploring, mapping, and testing IVR (Interactive Voice Response) phone trees. 

Built for permissioned testing, the IVR Suite uses **Twilio** for inbound/outbound telephony, **Deepgram** for real-time transcription, and **ngrok** for local webhook tunneling to provide a rich feature set for assessing and mapping complex IVR systems.

---

## Core Features

- **Live Mapping GUI:** A self-contained local web interface (`http://localhost:8080`) that provides live transcripts, call timers, one-click DTMF/speech injection, and a real-time visual graph of the discovered IVR nodes.
- **Automated Discovery Loop:** An iterative depth-first search (DFS) that automatically dials, listens, and explores unknown branches until an IVR tree is fully saturated (or hits user-defined safety bounds).
- **Test Suites:** A flexible batch testing system. Define test cases visually in the GUI or via the CLI wizard to trigger specific DTMF/speech responses when certain keywords are spoken by the IVR. Generates comprehensive Markdown reports.
- **AI Voice Generation:** Built-in OpenAI TTS integration for generating dynamic audio clips for testing.
- **Graph Building:** Groups structurally similar prompts, tracks announced vs. pressed options, and exports maps to JSON, Markdown, or Mermaid.js formats.

---

## Prerequisites

1. **Python 3.11+**
2. **ngrok** (for tunneling the local streaming server)
3. Provider Accounts:
   - **Twilio** (Account SID, Auth Token, and an active Phone Number)
   - **Deepgram** (API Key for transcription)
   - **OpenAI** (Optional, for TTS voice generation)

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

### 2. Test Suites
Run automated test cases where specific IVR phrases trigger specific DTMF/speech responses.

**Create a suite interactively:**
```bash
./run_ivr_assessor.sh test-suite-wizard --output suites/my_test.json
```

**Run a suite:**
```bash
./run_ivr_assessor.sh test-suite --suite suites/my_test.json --output reports/
```
*(Note: You can also visually create and run test suites directly inside the Live Map GUI!)*

### 3. Voice Generation
Generate high-quality TTS audio clips to use as injected speech responses.
```bash
./run_ivr_assessor.sh voice-generate --text "Representative please" --out clips/agent.wav --voice cedar
```

### 4. Utilities
- `map`: Run a single or multi-session map dynamically.
- `replay`: Reconstruct a mapped graph from a saved JSON trace.
- `dry-run`: Validate execution bounds and allowlist configuration without dialing.
- `sms-serve`: Run a local webhook server to bridge SMS replies into mapping jobs.

---
*For safety, the IVR Suite relies on an explicit allowlist architecture to prevent dialing unauthorized numbers.*