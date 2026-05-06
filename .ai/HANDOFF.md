# AI HANDOFF — IVRSuite
_Last updated: 2026-05-06 (production refactor Phases 0-5 complete)_

## Current Goal
Ship a complete, production-grade IVR phone-tree mapper with local-first audio pipeline and test-suite runner.

## Current State
- **170 tests passing, 0 failing** (`cd backend/python && .venv/bin/python -m pytest -q`)
- Active branch: `main`
- GUI runs at `http://localhost:8080` via `./run_ivr_assessor.sh live-map-gui`
- ngrok tunnel still in use (Cloudflare Tunnel is Phase 6 — not yet done)
- All credentials in `.env` at repo root (gitignored)

## ⚠️ ACTION REQUIRED: Rotate All Credentials
API credentials were visible during this session. Rotate before doing anything else:

| Credential | Where |
|---|---|
| `TWILIO_AUTH_TOKEN` | Twilio Console → Account → API Keys & Tokens |
| `DEEPGRAM_API_KEY` | Deepgram Console → API Keys → delete + create new |
| `OPENAI_API_KEY` | platform.openai.com → API Keys → delete + create new |
| `ASSEMBLYAI_API_KEY` | AssemblyAI Dashboard → API Keys → regenerate |
| `IVR_STREAM_AUTH_TOKEN` | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` |

## New Hot Path (Phases 0-5 complete)
```
Twilio μ-law 8kHz
→ audio_pipeline.py  (decode → 16kHz PCM → normalize → WebRTC VAD)
→ stt_service.py     (FasterWhisper local, free — STT_BACKEND=faster-whisper)
→ transcript_filter.py (dedup rolling window + length gate)
→ [existing DFS routing — unchanged]
→ tts_service.py     (Piper local, free — TTS_BACKEND=piper)
→ twilio_client.py   (unchanged)
```

Deepgram and OpenAI TTS still work as fallbacks via env vars:
- `STT_BACKEND=deepgram` → DeepgramTranscriber (existing, unchanged)
- `TTS_BACKEND=openai` → OpenAITTS (wraps ai_voice.py)

## What Changed This Session (Phases 0-5)

### New files
| File | Purpose |
|---|---|
| `backend/python/src/ivr_assessor/audio_pipeline.py` | μ-law decode, 16kHz resample, normalize, WebRTC VAD |
| `backend/python/src/ivr_assessor/stt_service.py` | FasterWhisperTranscriber + factory, Deepgram fallback |
| `backend/python/src/ivr_assessor/transcript_filter.py` | Confidence gate + dedup rolling window |
| `backend/python/src/ivr_assessor/tts_service.py` | PiperTTS + LRU cache + OpenAITTS fallback |
| `backend/python/src/ivr_assessor/logging_config.py` | structlog with call_sid/session_id context binding |
| `backend/python/tests/test_audio_pipeline.py` | 18 tests |
| `backend/python/tests/test_stt_service.py` | 16 tests |
| `backend/python/tests/test_transcript_filter.py` | 15 tests |
| `backend/python/tests/test_tts_service.py` | 14 tests |
| `.pre-commit-config.yaml` | detect-secrets + standard pre-commit hooks |

### Modified files
- `streaming_server.py` — VAD integration, transcriber factory, filter wiring, bounded audio buffer, `/healthz` endpoint, `_active_streams` counter
- `transcription.py` — added `INPUT_FORMAT = "mulaw_8k"` class attribute to DeepgramTranscriber
- `pyproject.toml` — added: `webrtcvad-wheels`, `faster-whisper`, `numpy`, `structlog`; optional groups: `performance`, `gpu`, `benchmarks`, `dev`
- `.gitignore` — added: `*.wav`, `*.mp3`, `recordings/`, `*.onnx`, `*.onnx.json`, `voices/`, `.cache/`, `.secrets.baseline`

## Phases Still Pending

### Phase 6 — Docker + Cloudflare Tunnel
- `docker/api/Dockerfile` — FastAPI + streaming server
- `docker/stt/Dockerfile` — FasterWhisper model pre-warmer
- `docker/tts/Dockerfile` — Piper binary + voice model download
- `docker-compose.yml` — orchestration with whisper_cache and piper_voices volumes
- `cloudflare_tunnel.py` — async subprocess wrapper for cloudflared
- Update `run_ivr_assessor.sh` with `TUNNEL_BACKEND=ngrok|cloudflare|none`

### Phase 7 — WER Benchmarks
- `benchmarks/wer_benchmark.py` — WERBenchmark class, BenchmarkReport dataclass
- `tests/test_wer_benchmark.py` — ~5 tests (metric math only, no real STT)
- `tests/fixtures/audio/` — WAV + ground truth transcript pairs
- Dep: `jiwer>=3.0` (already in `[benchmarks]` optional group)

## User Actions Required (not automated)

### Install Piper TTS (for local TTS)
```bash
brew install piper-tts
# Download voice model:
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -LO https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
# Add to .env:
# PIPER_VOICE=/path/to/en_US-lessac-medium.onnx
# TTS_BACKEND=piper
```

### Activate FasterWhisper STT
```bash
# Add to .env:
# STT_BACKEND=faster-whisper
# WHISPER_MODEL=small.en
# Model downloads automatically on first connect() to ~/.cache/huggingface/hub/
```

### Set up pre-commit
```bash
pip install pre-commit detect-secrets
pre-commit install
detect-secrets scan > .secrets.baseline
```

## Decisions Made (do not re-ask)
| Question | Answer |
|---|---|
| Redesign layout | Cockpit (A) — 320px right rail |
| DTMF detection | Strict: `/^[\s0-9*#]+$/` only |
| Discovery loop strategy | DFS — deepest unexplored option |
| Stopping condition | 2 consecutive no-progress calls |
| Test format | JSON ground truth + CLI runner (`test-suite` command) |
| Auto-pilot toggle location | Top of rail, above smart input |
| Flow editor / presets | Removed — test_suite.py supersedes them |
| Stream auth | Hash of TWILIO_ACCOUNT_SID:TWILIO_AUTH_TOKEN (not random); or `IVR_STREAM_AUTH_TOKEN` env var |
| Test suite data intake | Pipe-delimited schema row + data row (28 columns); `$varname` interpolation in responses |
| STT backend (local) | FasterWhisper via `stt_service.py`; Deepgram is fallback |
| TTS backend (local) | Piper via `tts_service.py`; OpenAI is fallback |
| VAD silence threshold | 15 frames = 300ms |
| VAD max segment | 1500 frames = 30s (hard cap, force emit) |
| Whisper confidence gate | exp(avg_logprob) >= 0.6 — lower is dropped |
| Transcript dedup window | Rolling 3-utterance window, case-insensitive |
| TTS LRU cache | 200 entries, pre-warmed with 20 common IVR phrases |
| webrtcvad package | `webrtcvad-wheels` (not `webrtcvad` — broken with setuptools 82+) |
| audioop on Python 3.13 | `audioop-lts>=0.2.1; python_version >= '3.13'` |

## Files To Check First
- `backend/python/src/ivr_assessor/streaming_server.py` — Twilio WS, VAD, transcriber factory, filter wiring
- `backend/python/src/ivr_assessor/audio_pipeline.py` — μ-law decode, VAD
- `backend/python/src/ivr_assessor/stt_service.py` — FasterWhisper transcriber + factory
- `backend/python/src/ivr_assessor/transcript_filter.py` — dedup filter
- `backend/python/src/ivr_assessor/tts_service.py` — Piper TTS + LRU cache
- `backend/python/src/ivr_assessor/live_map_gui.py` — GUI + all API endpoints
- `backend/python/src/ivr_assessor/test_suite.py` — batch test runner
- `backend/python/tests/` — 170 tests, all passing

## Rules For Future AI
- Read this file first. Update it before ending work.
- Do not duplicate logic — the old `flow` system is gone; `test_suite.py` is the replacement.
- Preserve all existing JS hooks in `live_map_gui.py` (`poll`, `padPress`, `sendInput`, etc.).
- `test_suite.py` dataclasses are named `Test*` — pytest warns about collection; harmless.
- Always run `cd backend/python && .venv/bin/python -m pytest -q` before committing.
- `.env` is gitignored but `.env.example` (at both repo root and `backend/python/`) documents all vars.
- Routing logic in `discovery_loop.py`, `prompt_intelligence.py`, `scenario_runner.py` is deterministic — do NOT add LLMs to the hot path.
- The plan file at `/Users/cameroncohen/.claude/plans/gleaming-frolicking-narwhal.md` is the authoritative implementation plan. Phases 0-5 are complete.

## Next Actions
1. **Rotate all credentials** (see warning above — do this first)
2. **Phase 6**: Docker + Cloudflare Tunnel (see plan file for full spec)
3. **Phase 7**: WER benchmarks (see plan file for full spec)
4. **Smoke test local pipeline**: set `STT_BACKEND=faster-whisper` + `TTS_BACKEND=piper` in `.env`, run `./run_ivr_assessor.sh live-map-gui`, make a test call
