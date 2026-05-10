# IVR Assessor Operations Runbook

## 1) Preflight checklist

- Python 3.11+
- Virtual environment created at `backend/python/.venv` (recommended)
- Dependencies installed: `python -m pip install -e backend/python`
- `.env` populated from `.env.example` for live usage

## 2) Startup modes

### Scripted / offline

```bash
./run_ivr_assessor.sh map --target-number +15555550100 --prompt "Press 1 for billing"
```

### Iterative discovery loop

```bash
./run_ivr_assessor.sh iterate-map --target-number +15555550100 --max-calls 12 --wall-clock-cap-s 30
```

### Live GUI mode

```bash
./run_ivr_assessor.sh live-map-gui
```

Expected defaults:
- GUI: `http://localhost:8080`
- Stream server: `http://127.0.0.1:8081`

## 3) Test suite and quality gate

Run full tests:

```bash
cd backend/python && python -m pytest -q
```

Release gate baseline:
- Tests pass (`0` failures)
- No unauthorized stream connection when tokenized URL is used
- CLI help/version commands succeed

## 4) Troubleshooting quick guide

### Replay artifact inspection

Inspect a replay trace deterministically:

```bash
./run_ivr_assessor.sh inspect-replay --trace-path backend/python/tests/fixtures/sample_ivr_trace.json
```

Emit JSON instead of text:

```bash
./run_ivr_assessor.sh inspect-replay --trace-path /path/to/replay.json --format json
```

### Runtime diagnostics

Inspect a live GUI/runtime directly:

```bash
./run_ivr_assessor.sh inspect-runtime --runtime-url http://127.0.0.1:8080/api/runtime-diagnostics
```

Inspect a saved metrics payload offline:

```bash
./run_ivr_assessor.sh inspect-runtime --metrics-path /path/to/runtime_metrics.json
```

Direct HTTP view for operators:

```bash
curl http://127.0.0.1:8080/api/runtime-diagnostics
```

### Unauthorized stream connection

Symptoms:
- `[stream] rejected unauthorized connection to /stream`

Checks:
1. Ensure both GUI and stream server use the same token source.
2. Prefer setting `IVR_STREAM_AUTH_TOKEN` explicitly in `.env`.
3. If manually setting `IVR_STREAM_URL`, remove stale `?token=` and let app append current token.

### Twilio/Deepgram live issues

Checks:
1. Verify `TWILIO_*` variables are set and valid.
2. Verify `DEEPGRAM_API_KEY` is set.
3. Confirm ngrok URL is current and reachable.

## 5) Security baseline

- Never commit real credentials.
- Avoid sharing logs containing account IDs, auth tokens, or stream query tokens.
- Keep Twilio signature validation enabled unless explicitly debugging locally.
