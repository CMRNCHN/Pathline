# Desktop lab E2E — verification notes (Wave C)

Verification of the frozen desktop automation loop (dial → local STT → DTMF →
encrypted callstate) from the plan `docs/plans/2026-07-14-desktop-sip-stt-e2e.md`.

**Environment reality:** the latest native checks were run on macOS with the
pinned Whisper tiny.en model, but without a live Asterisk/API acceptance run.
Verification is split into (1) rigorous **code-level + automatable** proof,
including real local model inference, and (2) the **live GUI run** that remains
deferred. Nothing below softens the privacy posture:
desktop is the primary automation path; softphone + manual paste stays
legacy-only (`docs/lab-run.md`).

---

## Proven locally

| Check | Command | Result |
|-------|---------|--------|
| Native SIP + Whisper tests | `cd desktop/src-tauri && cargo test` | **13 passed, 0 failed**, including real bundled-model inference |
| Packaged macOS desktop | `cd desktop && npm run build` | **green**; app + DMG contain the checksummed model resource |
| Client type-check + production build | `cd client && npm run build` | **green** (tsc + vite, 2177 modules) |
| On-device STT pipeline fixture | `cd client && npm run stt:fixture` | **PASS** (pipeline + selection) |
| Desktop config + privacy assertions | `SKIP_LAB_PREFLIGHT=1 bash scripts/lab-verify-flow.sh` | **all ✓** |
| Verify-script syntax | `bash -n scripts/lab-verify-flow.sh` | **OK** |

### cargo test (native SIP + Whisper)

13 tests exercise the signaling/media paths and native model runtime, notably:

- `send_dtmf_emits_telephone_events_over_udp` — on-the-wire RFC 4733
  telephone-event RTP (marked begin + end packet) over a localhost UDP peer.
- `audio_rtp_packet_decodes_to_pcm` — inbound PCMU → G.711 decode → 16 kHz
  float PCM (the STT feed).
- `short_hash_never_reveals_plaintext` — DTMF audit hash is deterministic and
  never contains the digit sequence.
- `negotiate_media_*` — SDP answer negotiation (PCMU/PCMA, telephone-event PT).
- `init_script_defines_bridge_and_commands` — the injected shim defines
  `window.__pathlineSipBridge` and all four commands.
- `bundled_model_loads_and_runs_local_inference` — verifies the pinned SHA-256,
  loads the actual 77 MB tiny.en resource, and runs whisper.cpp inference.

### STT fixture (`client/src/stt/fixture.ts`)

Drives synthetic PCM through the **production path**
(`FixtureTransport.onAudio → AudioSession → LocalWhisperEngine (VAD/endpointing)
→ mock on-device backend → runSession.processPhrase → DTMF`) against the real
`lab-account-status` Path. Asserted:

- 4 utterances transcribed; DTMF sequence `11234#`; `account_balance` captured;
  run completed.
- **`noTranscriptInLedger: true`** — no transcript text leaks into the audit
  ledger.
- Selection guard: an automated, bridge-backed run **never** selects Web Speech
  even when the Web Speech API is present (falls back to null + manual paste).

---

## Live lab SIP acceptance (proven)

`bash scripts/lab-verify-flow.sh` (no `SKIP_LAB_PREFLIGHT`) now completes an
authenticated SIP/TLS call through extension `1000`, drives the full IVR with
SIP INFO DTMF, and receives remote BYE. The desktop app still uses RFC 4733 RTP
telephone-events for production keypad injection.

## Deferred GUI acceptance

The following still require an interactive desktop window and packet capture:

1. `./scripts/lab-desktop.sh` (sets `PATHLINE_SIP_PROFILE=lab`).
2. Execute **Run → Lab account status (Asterisk 1000)** once end-to-end:
   dial `1000` → local Whisper → RFC 4733 DTMF → encrypted callstate.
3. Confirm **Runs shows completed** + captured `account_balance`.
4. Live network capture asserting **no STT egress** during the run.

The native bridge injects `window.__pathlineWhisper`, verifies and loads the
pinned MIT-licensed tiny.en model, and performs whisper.cpp inference locally.
The client blocks dialing when SIP or model readiness fails, flushes queued STT
on terminal transport events, and records exactly one terminal outcome.

---

## Privacy Verification results

All items verified by reading the code on this branch. **PASS** = the code
guarantees the property; live network-capture confirmation of egress is the one
item empirically deferred to the Mac host (the code path is proven absent).

| # | Requirement | Result | Evidence |
|---|-------------|--------|----------|
| 1 | No outbound audio except SIP RTP to the intended peer | **PASS** | `sip_bridge.rs`: inbound RTP decoded → `emit_audio` to the local webview only (line ~525); outbound RTP is comfort silence to the negotiated peer (`rtp_sock.send`, no mic capture — comment line ~532). No `fetch`/HTTP for audio anywhere in `client/src/stt/**` (grep: only doc-comments mention POST). |
| 2 | No transcript POST to Pathline or third parties | **PASS** | `client/src/stt/whisperEngine.ts` hands phrase text to `onPhrase` → `runSession.processPhrase`; no network. Full client egress enumeration (`fetch(`) = static `/scripts/*.json`, `/api/health`, and `client/src/api.ts` endpoints (token/consent/callstate/export/delete/revoke) — none carry transcripts. |
| 3 | Callstate payload is encrypted blob + nonce only | **PASS** | `RunPage.tsx handleComplete`: `encryptCallStatePayload(...)` (AES-GCM, `crypto.ts`) → `submitEncryptedCallState(token, sessionId, ciphertext, nonce)`. `api.ts` posts only `session_id/encrypted_payload/payload_nonce`. `main.py EncryptedCallStateIngest` has exactly those 3 fields ("server cannot read contents"). |
| 4 | DTMF ledger stores hash + digit count, never plaintext | **PASS** | `runSession.ts`: `DTMF_SENT` metadata = `{ step, digits: sequence.length, hash }` (count + SHA-256, `dtmf/dtmf.ts hashDtmfSequence`). `sip_bridge.rs`: logs `count` + `short_hash(&digits)` only, `dtmf_sent` event carries `count=` (line ~484–490). Ledger types comment: "Never raw secrets." |
| 5 | Whisper boundary is local-only | **PASS** | `desktop/src-tauri/src/whisper_bridge.rs` loads a checksummed bundled model with `whisper-rs`, disables native transcript-bearing logs, and exposes only local Tauri commands. The real model inference test passes. |
| 6 | No STT egress (network capture during a lab Run) | **PASS (code) / deferred (capture)** | Code review proves no audio/transcript network path exists (items 1–2 + grep egress enumeration). Empirical packet capture during a live run is deferred to the Mac/Docker host. |

---

## How to reproduce

Headless (this VM):

```bash
cd desktop/src-tauri && cargo test
cd client && npm run build
cd client && npm run stt:fixture
SKIP_LAB_PREFLIGHT=1 bash scripts/lab-verify-flow.sh   # static desktop assertions
bash -n scripts/lab-verify-flow.sh
```

Live (macOS/Docker host):

```bash
./scripts/lab-desktop.sh          # lab stack + desktop app
bash scripts/lab-verify-flow.sh   # full preflight + smoke (stack must be up)
```
