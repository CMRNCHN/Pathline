---
name: desktop-whisper-bridge
description: Implements an on-device whisper.cpp backend in the Tauri shell that injects window.__pathlineWhisper for the STT pipeline. Use proactively to close the real-STT gap after the desktop loop is merged.
---

You give Pathline desktop a real, on-device speech-to-text backend.

## Preconditions
- `client/src/stt/whisperEngine.ts` already probes for `window.__pathlineWhisper` / a WASM backend.
- `docs/desktop-audio-contract.md` frozen (mono float32, 16 kHz). Base off `origin/cursor/desktop-next-0880`.

## Owns exclusively
- `desktop/src-tauri/src/whisper_bridge.rs` (new)
- `desktop/src-tauri/src/lib.rs` (inject `window.__pathlineWhisper` only — minimal edits, alongside the SIP shim)
- `desktop/src-tauri/Cargo.toml` (whisper deps)

## Interface (match the client probe — do not invent)
Inject `window.__pathlineWhisper` with `transcribe(pcm: Float32Array|number[], sampleRate) -> Promise<string>`,
runnable before the webview content, backed by a `#[tauri::command]`.

## Implementation notes
- Use a pure/FFI whisper.cpp Rust binding that runs ENTIRELY on device. No cloud/SaaS, no network.
- Model: load a small model (tiny/base) from a configured local path (env or app data dir);
  document download-vs-bundle. Fail gracefully (capability probe returns false) if the model is missing.
- Expect 16 kHz mono float32 per the audio contract; resample only if unavoidable.

## Must NOT
- Edit `client/src/stt/**` engine logic, `sip_bridge.rs`, `RunSession`, or `runEngine`.
- POST audio/transcripts anywhere; log transcript text.

## Verify
- `cd desktop/src-tauri && cargo check`/`cargo test` (report; installing Tauri Linux libs if needed).
- `cd client && npm run build` + `npm run stt:fixture` still green.
- Honest note: real transcription accuracy needs a bundled model on a macOS/desktop host.
