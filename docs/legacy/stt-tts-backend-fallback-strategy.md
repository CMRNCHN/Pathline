# Bounded STT/TTS Backend Fallback Strategy

## Status

Planning artifact only. This document does not authorize runtime, hot-path, topology, websocket/protocol, replay, storage, route, suite, traversal, or response-automation changes.

Authoritative governance source: `.ai/plans/ivr-phase-operations-anchor.md`.

The strategy preserves the current hot path shape:

```text
Twilio μ-law audio
→ audio_pipeline.py
→ stt_service.py
→ transcript_filter.py
→ deterministic DFS routing
→ tts_service.py
→ Twilio response
```

Future implementation must keep backend selection deterministic, bounded, replayable, observable, and operator-visible. Backend fallback must be resolved before a run starts, not by autonomous routing during a call.

## Goals

- Keep IVRSuite local-first when model downloads or binary hosts are unavailable.
- Provide operationally useful degraded modes for Suite Planning / Configuration and Live Operations / Active Run.
- Make missing model/binary/API prerequisites visible before route discovery or suite execution begins.
- Avoid mid-call backend churn, hidden network downloads, or unbounded retries.
- Keep OpenAI/cloud STT and TTS as explicit optional fallbacks only.

## Non-Goals

- No engine implementation in this slice.
- No changes to audio segmentation, VAD timing, transcript filtering, deterministic DFS traversal, response automation, websocket events, token auth, replay artifacts, or server topology.
- No automatic cloud use unless the operator explicitly enables it.
- No model downloads from the runtime hot path.
- No broad plugin framework, dependency injection container, agentic routing, or LLM-based runtime decision-making.

## Recommended Abstraction Boundaries

### STT Boundary

Keep the current `stt_service.py` factory as the public boundary for runtime selection.

Future implementation should introduce only small, explicit helper boundaries inside or adjacent to `stt_service.py`:

- `BackendSpec`: static backend metadata used for preflight and status labels.
- `AvailabilityResult`: deterministic result with `available`, `degraded`, `reason`, `operator_action`, and `network_required` fields.
- `resolve_stt_backend(config)`: pre-run selection function that returns one backend name plus an availability/degraded-mode explanation.
- Existing transcriber contract remains unchanged: `connect()`, `process_audio(bytes)`, `close()`, `stats()`, and `INPUT_FORMAT`.

The runtime should still receive exactly one transcriber instance. If the selected backend cannot connect, the run should fail closed or enter an explicitly selected degraded mode before route discovery begins.

### TTS Boundary

Keep the current `tts_service.py` factory as the public boundary for runtime selection.

Future implementation should introduce similarly small helper boundaries:

- `TTSBackendSpec`: static engine metadata and required local assets.
- `TTSAvailabilityResult`: deterministic preflight result with binary/model/cache/API-key state.
- `resolve_tts_backend(config)`: pre-run selection function that returns one engine plus degraded-mode explanation.
- Existing synthesizer contract remains unchanged: `synthesize(text: str) -> bytes` returning Twilio-compatible μ-law 8 kHz bytes.

The runtime should still receive exactly one TTS engine. Fallback should not swap voices or engines mid-call unless a later approved plan defines a deterministic pre-rendered phrase-only mode.

### Shared Preflight Boundary

Add a future non-hot-path preflight utility for Suite Planning / Configuration:

- Runs model/binary/cache/API-key checks before calls begin.
- Produces operator-facing status for the GUI and logs using existing status/metrics surfaces.
- Does not create a websocket event, protocol field, replay semantic, or new storage contract unless separately approved.
- Must not download models by default; downloads or cache population are explicit operator actions outside active runs.

## Engine Matrix

| Engine | Type | Runtime Role | Strengths | Limitations | Network Use | Recommended Status |
|---|---|---|---|---|---|---|
| Simulated STT | Deterministic local script | Operational validation and degraded transcript flow | No model, no binary, deterministic, validates downstream transcript handling | Not real speech recognition; not valid for checkpoint evidence | None | Already available; keep explicit and label as simulation |
| Apple Speech.framework | OS-native local/on-device when available | macOS local STT fallback | No HF download; operator-friendly on macOS; may use system speech assets | macOS-only; PyObjC bridge likely needed; availability/language behavior must be probed | Should be treated as local-only only when confirmed | Future local fallback candidate |
| whisper.cpp | Local binary/model | Local STT fallback | Small binaries; GGML/GGUF cache is easy to vendor/pre-seed; good offline story | Separate binary and model management; streaming integration needs bounded subprocess handling | None after cache seed | Strong future offline fallback |
| faster-whisper / CTranslate2 | Local Python model | Default local STT | Already implemented; CPU/GPU support; current stats expose model/cache fields | HF cache/download failure blocks startup unless cache/path is prepared | Optional only during explicit provisioning, not active run | Keep as default real STT when verified |
| Vosk / lightweight offline ASR | Local model | Last-resort real offline STT | Small models; predictable offline operation; no HF dependency | Lower accuracy on noisy IVR prompts; grammar tuning may be needed | None after cache seed | Useful degraded real-STT fallback |
| Deepgram | Cloud STT | Existing optional cloud STT | Already wired; real-time cloud quality | Requires key/network; not local-first | Yes | Optional explicit fallback only |
| OpenAI/cloud STT | Cloud STT | Optional fallback or post-run transcription | Strong accuracy and broad model support | Requires key/network/cost; must not be default | Yes | Optional explicit fallback only, never implicit |
| Piper | Local TTS binary/model | Default local TTS | Already implemented; local-first; μ-law conversion and LRU cache exist | Requires binary and ONNX voice; host downloads can fail | None after cache seed | Keep as default when verified |
| macOS `say` / pre-rendered system voice | OS-native local TTS | Degraded local TTS fallback | No external model host; useful on operator Mac | Voice consistency differs; conversion path must be bounded | None | Future phrase/utility fallback candidate |
| Pre-rendered phrase cache | Local artifacts | Degraded TTS mode | Most deterministic; no runtime synthesis needed for common IVR responses | Limited phrase coverage; cannot synthesize arbitrary prompts | None | Strong degraded mode for common response automation |
| OpenAI TTS | Cloud TTS | Existing optional cloud TTS | Already wired; high-quality voice | Requires key/network/cost; not local-first | Yes | Optional explicit fallback only |

## Fallback Order

Fallback must be deterministic and selected before Live Operations / Active Run starts.

### STT Default Profile

Use this order only when `STT_BACKEND=auto-local` or a future equivalent explicit setting is approved:

1. `faster-whisper` with `WHISPER_MODEL_PATH` or verified local cache.
2. `whisper.cpp` with verified binary and local model file.
3. Apple Speech.framework when running on macOS and local/on-device availability is confirmed.
4. Vosk/lightweight offline ASR with verified local model directory.
5. `simulated` only if the operator explicitly allows simulated degraded transcript mode.
6. OpenAI/cloud STT only if the operator explicitly enables cloud fallback and required credentials/network checks pass.

Current explicit `STT_BACKEND` values should remain authoritative. If the operator sets `STT_BACKEND=faster-whisper`, a missing model should produce a clear unavailable/degraded message rather than silently switching to cloud.

### STT Operational Validation Profile

Use for testing downstream runtime/media flow without real STT:

1. `simulated`.
2. No automatic escalation to real or cloud STT.

This profile is useful when external model provisioning is blocked but operators need to validate transcript filtering, prompt timeline behavior, and deterministic traversal supervision with known transcript events.

### TTS Default Profile

Use this order only when `TTS_BACKEND=auto-local` or a future equivalent explicit setting is approved:

1. `piper` with verified binary, voice model, and JSON sidecar if required by the voice.
2. Pre-rendered phrase cache for known response automation phrases.
3. macOS local TTS (`say` or SpeechSynthesizer-backed rendering) when available and conversion to μ-law 8 kHz is verified.
4. Silent/no-spoken-response degraded mode only for manual/operator-supervised scenarios where keypad responses remain valid.
5. OpenAI TTS only if the operator explicitly enables cloud fallback and required credentials/network checks pass.

Current explicit `TTS_BACKEND` values should remain authoritative. If the operator sets `TTS_BACKEND=piper`, missing binary/model state should be reported clearly rather than silently switching to OpenAI.

## Degraded-Mode Behavior

### Degraded STT: Simulated Transcript Backend

- Label every status message and diagnostic as simulated, not transcribed speech.
- Keep transcript script deterministic and bounded.
- Do not persist simulated output as evidence equivalent to real audio transcription unless a separate approved replay/report plan adds explicit provenance fields.
- Use only for operational validation, smoke tests, and controlled demos.
- Preserve downstream semantics: transcript callbacks keep the same shape and pass through the existing transcript filter.

### Degraded STT: Real Offline Fallbacks

- If `faster-whisper` is unavailable but another local backend is selected pre-run, report the selected engine, model path, language, and expected limitations.
- Enforce bounded queues and subprocess timeouts for any future binary-backed engine.
- Do not download models from `connect()` or `process_audio()` unless an explicit provisioning command was run before the active run.
- Do not change confidence gates, transcript filter semantics, or traversal logic without a separate approved runtime plan.

### Degraded STT: Cloud Fallback

- Require explicit opt-in such as `STT_ALLOW_CLOUD_FALLBACK=true` plus backend/API-key configuration.
- Show a pre-run warning that audio leaves the local machine.
- Never use cloud STT as a hidden automatic fallback from a local backend failure.
- Bound connection retries and fail closed if cloud connection cannot be established before the run.

### Degraded TTS: Phrase Cache / Local OS Voice

- Prefer deterministic pre-rendered phrase artifacts for common response automation phrases.
- Label phrase-only mode as limited coverage.
- If arbitrary spoken responses are requested outside cache coverage, fail that synthesis request with an operator-visible message rather than blocking or switching to cloud silently.
- Keep keypad/DTMF response automation unaffected when spoken TTS is unavailable.

### Degraded TTS: No-Spoken-Response Mode

- Permit only when the planned route or suite can proceed without spoken prompts from IVRSuite.
- Make the status explicit: “TTS unavailable; spoken response automation disabled; keypad/manual responses only.”
- Do not change route discovery or suite execution semantics. This is a capability constraint, not a traversal decision.

### Degraded TTS: Cloud Fallback

- Require explicit opt-in such as `TTS_ALLOW_CLOUD_FALLBACK=true` plus API-key configuration.
- Show a pre-run warning that text prompts are sent to a cloud provider.
- Do not silently switch from Piper to OpenAI on missing binary/model state.

## Local Model Cache Strategy

### Cache Layout

Use a single operator-visible model root in future planning, for example `~/.ivr_assessor/models/`, with backend-specific subdirectories:

```text
~/.ivr_assessor/models/
├── faster-whisper/
├── whisper.cpp/
├── vosk/
├── piper/
└── manifests/
```

This is a future storage addition and requires separate implementation approval because it adds storage paths. If implemented, storage constants should be centralized rather than scattered.

### Manifest Strategy

Each model directory should have a small manifest generated during explicit provisioning:

- backend name and version.
- model name, language, and expected sample format.
- local file paths.
- file sizes and SHA256 hashes for required artifacts.
- source URL or package origin for audit only.
- created/verified timestamp.
- minimum compatible engine version when known.

Runtime preflight should read manifests and verify files/hashes. It should not contact external hosts unless the operator invoked a provisioning/check command that explicitly allows network access.

### Provisioning Strategy

Provisioning should be separate from active runs:

- `prepare-models` or equivalent future CLI action downloads or copies models.
- `verify-models` or equivalent future CLI action checks local files without downloading.
- GUI Suite Planning / Configuration can display verification state but should not start implicit downloads.
- Offline install bundles should be supported by copying model directories plus manifests into the cache root.

## Model Availability Checks

### STT Checks

For each STT backend, preflight should return `available`, `degraded`, or `unavailable`:

- `simulated`: always available; degraded because it is not real STT.
- `faster-whisper`: check importability, model path/cache presence, `local_files_only` state, device/compute compatibility, and optional cache manifest hash.
- `whisper.cpp`: check binary executable, model file/hash, invocation smoke command, and output parsing readiness.
- Apple Speech.framework: check platform, framework/PyObjC importability, recognizer availability, language support, and local/on-device mode if required.
- Vosk/lightweight ASR: check package/binary importability, model directory/hash, language metadata, and decode smoke fixture.
- Cloud STT: check explicit opt-in, API key, network policy setting, and bounded authentication/connectivity probe.

### TTS Checks

For each TTS backend, preflight should return `available`, `degraded`, or `unavailable`:

- `piper`: check binary executable, voice ONNX, sidecar JSON if required, sample-rate setting, and one short synthesis smoke output.
- phrase cache: check required phrase artifact set, μ-law 8 kHz format, and hash manifest.
- macOS local TTS: check platform command/framework availability and bounded render/convert smoke output.
- no-spoken-response: always available only as degraded manual/keypad mode.
- OpenAI TTS: check explicit opt-in, API key, network policy setting, and bounded API/client initialization.

### Health and Messaging

Future status payloads should remain additive and avoid protocol changes unless separately approved. Candidate wording:

- “STT backend unavailable: faster-whisper model not found in local cache. Active runs cannot start with real local STT until a model is provisioned or a degraded mode is selected.”
- “STT degraded: simulated transcript backend selected. Output validates downstream flow but is not evidence of heard IVR audio.”
- “TTS degraded: Piper voice unavailable. Spoken response automation disabled; keypad/manual responses remain available.”
- “Cloud fallback enabled: audio/text may leave this machine for the selected provider.”

## Testing Strategy

### Unit Tests

- Backend resolution preserves explicit `STT_BACKEND` and `TTS_BACKEND` values.
- Auto-local resolution chooses the first verified local backend and never chooses cloud unless explicit cloud fallback is enabled.
- Missing model/binary/API-key states produce deterministic `AvailabilityResult` values.
- Simulated STT remains deterministic and bounded.
- TTS phrase-cache degraded mode fails uncovered phrases clearly.
- Cache manifest verification detects missing files, wrong hashes, and incompatible backend labels.

### Integration Tests

- Preflight blocks active run startup when selected real STT/TTS backend is unavailable and no degraded mode is selected.
- Preflight allows operational validation with simulated STT and labels it as degraded.
- Existing websocket auth/connect behavior is unchanged.
- Existing transcript filter and replay tests remain unchanged.
- Recording/post-run transcription behavior is not changed by live STT fallback planning unless separately scoped.

### Smoke Tests

- Local default: `STT_BACKEND=faster-whisper`, `TTS_BACKEND=piper`, verified cache, no network.
- Offline fallback: `STT_BACKEND=auto-local`, missing faster-whisper cache, verified whisper.cpp or Vosk cache.
- Simulated validation: `STT_BACKEND=simulated`, no model assets.
- TTS degraded: missing Piper voice, phrase cache or no-spoken-response mode selected explicitly.
- Cloud fallback: explicit cloud allow flag and API key set; verify opt-in messaging and bounded connection failure handling.

### Regression Tests

Run targeted tests first, then broader tests when implementation eventually touches code:

```bash
pytest backend/python/tests/test_stt_service.py backend/python/tests/test_tts_service.py -q
pytest backend/python/tests/test_streaming_server_auth.py backend/python/tests/test_transcript_filter.py -q
pytest backend/python/tests/ -q
```

For this planning-only document, repository tests are not required; targeted governance/doc verification is sufficient.

## Implementation Slices for Later

### Slice 1 — Planning/Preflight Data Only

- Add static backend metadata and availability result dataclasses.
- Add deterministic local checks for currently implemented `faster-whisper`, `simulated`, `piper`, Deepgram, and OpenAI TTS.
- Add tests for resolution and availability results.
- No runtime backend fallback yet.

### Slice 2 — Local Cache Verification

- Add approved storage constants for model cache roots.
- Add manifest read/verify helpers.
- Add CLI or GUI preflight display for cache state.
- No downloads during active runs.

### Slice 3 — Explicit Auto-Local Resolution

- Add `auto-local` selection for STT/TTS after tests prove deterministic ordering.
- Preserve explicit backend settings as authoritative.
- Emit degraded-mode status before active runs.
- No websocket/protocol or replay changes.

### Slice 4 — whisper.cpp or Vosk Backend

- Add one local offline STT engine behind the unchanged transcriber contract.
- Prefer the engine with the simplest bounded subprocess/import and model-cache story.
- Add smoke fixture tests without network or live calls.

### Slice 5 — Apple Speech.framework Backend

- Add macOS-only availability checks.
- Add backend only if local/on-device behavior can be verified and bounded.
- Skip tests cleanly on non-macOS environments.

### Slice 6 — TTS Phrase Cache / OS Voice Degraded Mode

- Add explicit phrase-only or OS-voice degraded TTS mode.
- Verify μ-law 8 kHz output and phrase coverage.
- Keep arbitrary text failures explicit and operator-visible.

### Slice 7 — Optional Cloud Fallback Guardrails

- Add explicit cloud fallback allow flags.
- Add pre-run warnings and bounded probes.
- Keep cloud fallback opt-in only and never hidden behind local backend failure.

## Risks and Controls

- Risk: “Fallback” becomes hidden mid-call behavior. Control: resolve one backend pre-run and keep runtime backend fixed.
- Risk: cloud fallback weakens local-first guarantees. Control: require explicit allow flags and operator-visible warnings.
- Risk: model provisioning causes hot-path latency or network failure. Control: no downloads during active runs.
- Risk: additional engines increase conceptual complexity. Control: add one backend per implementation slice, behind the existing factory contract.
- Risk: degraded transcripts contaminate evidence. Control: label simulated/degraded provenance before any persisted report/replay changes are proposed.
