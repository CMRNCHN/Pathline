---
title: Desktop SIP + STT + E2E loop
date: 2026-07-14
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

# Desktop SIP + STT + E2E loop

## Goal Capsule

**Objective:** Prove the frozen desktop automation loop end-to-end — dial lab Asterisk over SIP, transcribe IVR locally, match phrases in `runEngine`, inject DTMF via transport, persist ledger + encrypted callstate — without audio or secrets leaving the device.

**Authority:** `docs/architecture-boundary.md` (frozen) · `docs/roadmap.md` v1 · `client-native/README.md`

**Stop when:**
1. Desktop app dials lab extension `1000` through `window.__promptpathSipBridge`
2. Local STT feeds `RunSession.processPhrase` without paste in automated mode
3. Lab Path completes with auto-DTMF and encrypted callstate ingest to thin API
4. `scripts/lab-verify-flow.sh` (desktop mode) exits green
5. Privacy Verification checklist passes

**Out of scope:** Mobile CallKit/Telecom, server STT/orchestrator, production DID pool, Users/admin multi-tenant, fatter backend APIs.

---

## Product Contract

### Requirements

| ID | Requirement |
|----|-------------|
| R1 | Client owns the media session via `CallTransport`; engine never talks SIP |
| R2 | Rust shell injects `NativeSipBridge` matching `client/src/transport/SipTransport.ts` |
| R3 | On-device STT only — no audio/transcripts to PromptPath servers |
| R4 | DTMF audit remains `{ step, digits, hash }` — never plaintext sequences in ledger |
| R5 | Lab Path `lab-account-status` runs automated on desktop (target + autoListen) |
| R6 | Fail closed when SIP/STT unavailable — clear transport `error` events, no silent `tel:` fallback |
| R7 | Parallel execution via dedicated Cursor subagents with exclusive file ownership |
| R8 | SIP stack is **one** vendor (Linphone **or** PJSIP) — never both |

### Actors & flows

1. Operator starts lab (`scripts/lab.sh`) + desktop (`npm run desktop:dev`)
2. Operator opens Workflows → Lab Path → Run (consent → configure → active)
3. Client dials SIP → IVR audio → local STT → phrase match → DTMF inject → ledger → encrypt → `POST /v1/callstate`
4. Operator verifies captured fields + System health + Privacy Verification

### Acceptance examples

- **Happy path:** Dial lab 1000 → hear main menu → auto-send `1` → complete PIN/SSN/status chain → Runs shows completed
- **SIP down:** Dial fails → UI shows transport error; no hang / blank window
- **STT unavailable:** Automated mode surfaces listen error; manual paste still works
- **Browser without simulate:** No false automation (`createAppTransport()` returns `null`)

### Failure matrix

| Failure | Expected |
|---------|----------|
| SIP unavailable / bad creds | Transport `error` event; Run shows failure; no silent dial |
| RTP timeout / call drop | `disconnected` / `CALL_ENDED` (abandoned); Run ends cleanly |
| Whisper unavailable | `stt:error` surfaced in UI; allow manual paste fallback |
| API unavailable at submit | Error on ingest; local Run History still records on-device result; no secret leakage |
| Vault / local keys cleared mid-run | Fail before ingest if encrypt cannot proceed; clear message |
| Invalid / empty DTMF from engine | Engine does not send; no crash; ledger has no plaintext digits |

---

## Planning Contract

### Key technical decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SIP stack | **Forced single choice via U0 scout** — default recommend **Linphone SDK** for macOS-first MVP | Better call/media abstraction; scout may pick PJSIP only with written rationale in `docs/desktop-sip-stack.md`. **Never both.** |
| Media format | PCM `Float32Array` + `sampleRate` on `onAudio` (mono default) | Matches existing `CallTransport` / `NativeSipBridge` |
| STT engine | **Whisper.cpp** local; Web Speech = browser-only fallback | Device STT; portable |
| Bridge injection | `window.__promptpathSipBridge` before/on webview ready | Consumed by `createSipTransport()` |
| Orchestration | Do **not** split `RunSession` | Frozen boundary |
| Fasttrack | Harden `.cursor/agents/desktop-*.md` then spawn parallel Tasks | Exclusive file ownership |

### Assumptions

- Wave 0–1 shipped: Tauri scaffold, `RunSession` wire, API sidecar, UI IA (`cursor/desktop-mvp-7a69`)
- Lab Asterisk via `./scripts/lab.sh`
- Thin API needs no new routes
- Mac is primary SIP/STT build host

### Deferred (non-blocking)

- Production SIP trunk providers
- Platform Speech as Whisper alternative
- Users / Integrations nav destinations

### Sequencing

```
U0  Subagent pack + SIP scout lock          ← serial gate
     │
U1  SIP bridge                              ← Wave A
U2  Lab Path config + docs                  ← Wave A parallel
     │
    Freeze audio contract (must not drift)
     │
U3  STT pipeline                            ← Wave B (after U1 onAudio)
     │
U4  E2E verify + integration merge          ← Wave C
```

---

## Frozen Runtime Contracts

Agents **must not** invent alternate transport/STT interfaces. These match the repo today.

### CallTransport (`client/src/transport/CallTransport.ts`)

```ts
interface CallTransport {
  dial(number: string): Promise<void>;
  answer(): Promise<void>;
  sendDTMF(digits: string, durationMs: number): Promise<void>;
  hangup(): Promise<void>;
  onAudio(handler: (pcm: Float32Array, sampleRate: number) => void): () => void;
  onEvent(handler: (event: TransportEvent) => void): () => void;
}

type TransportEventType =
  | "connected" | "disconnected" | "ringing"
  | "answered" | "dtmf_sent" | "error";
```

### NativeSipBridge (`client/src/transport/SipTransport.ts`)

```ts
interface NativeSipBridge {
  dial(number: string): Promise<void>;
  answer(): Promise<void>;
  sendDtmf(digits: string, durationMs: number): Promise<void>;
  hangup(): Promise<void>;
  onAudio(callback: (pcm: Float32Array, sampleRate: number) => void): () => void;
  onEvent(callback: (type: string, detail?: string) => void): () => void;
}
// Injected as window.__promptpathSipBridge
```

### Layer rules (non-negotiable)

| Layer | May know | Must NOT |
|-------|----------|----------|
| SIP / `sip_bridge.rs` | Dial, RTP, DTMF inject, PCM frames | Import `RunSession`, `runEngine`, UI |
| STT | PCM → text phrases | Import SIP stack / Rust bridge |
| `runEngine` / `RunSession` | Phrases, Path, DTMF **actions** via transport iface | SIP SDK, Whisper internals |
| Ledger | Hashed audit events | Secrets, transcripts, plaintext DTMF |
| API | Encrypted blobs + consent | Audio, phone numbers, transcripts |

### Audio contract defaults

Documented in `docs/desktop-audio-contract.md` (U0/U1):

- Sample rate: prefer **16 kHz** mono float32 for Whisper path (resample in bridge if needed)
- Frame delivery: continuous `onAudio` callbacks; STT owns VAD/endpointing
- Channels: mono unless explicitly extended later (do not break existing 2-arg signature)

---

## Implementation Units

### U0. Subagent pack + SIP scout lock

**Goal:** Create Cursor subagents with exclusive ownership; scout **locks one SIP stack**.

**Files:**
- `.cursor/agents/desktop-sip-scout.md`
- `.cursor/agents/desktop-sip-bridge.md`
- `.cursor/agents/desktop-audio-contract.md`
- `.cursor/agents/desktop-stt-pipeline.md`
- `.cursor/agents/desktop-lab-e2e.md`
- `.cursor/agents/desktop-integration.md`
- `docs/desktop-sip-stack.md` (scout output — single choice + install deps)
- `docs/desktop-audio-contract.md` (PCM/sample-rate freeze)

**Ownership matrix:**

| Agent | Owns exclusively |
|-------|------------------|
| `desktop-sip-scout` | `docs/desktop-sip-stack.md` only |
| `desktop-sip-bridge` | `desktop/src-tauri/src/sip_bridge.rs`, bridge inject in `lib.rs`, SIP deps in `Cargo.toml` / build scripts |
| `desktop-audio-contract` | `docs/desktop-audio-contract.md`, optional `client/src/transport/audioFormat.ts` constants |
| `desktop-stt-pipeline` | `client/src/stt/**`, `client/src/localStt.ts`, STT wiring in `RunActivePanel` / `AudioSession` consumers |
| `desktop-lab-e2e` | `client/public/scripts/lab-account-status.json`, `docs/lab-run.md`, `scripts/lab-verify-flow.sh`, optional `scripts/lab-desktop.sh` |
| `desktop-integration` | Merges only — no feature files |

**Acceptance:**
- [ ] One of Linphone / PJSIP chosen in `docs/desktop-sip-stack.md` with rationale
- [ ] Agent frontmatter valid; no overlapping exclusive paths
- [ ] Descriptions include proactive wave triggers

**Branch:** `cursor/desktop-agents-7a69` (or commit on `cursor/desktop-mvp-7a69`)

---

### U1. Native SIP bridge

**Goal:** Inject working `window.__promptpathSipBridge` so Tauri stops using `SimulatorTransport` for dial/DTMF.

**Files:**
- `desktop/src-tauri/src/sip_bridge.rs`
- `desktop/src-tauri/src/lib.rs`
- `desktop/src-tauri/Cargo.toml` (+ build tooling as needed)
- Consumes `docs/desktop-sip-stack.md` + `docs/desktop-audio-contract.md`

**Depends on:** U0 (stack lock)

**Approach:**
1. Implement `NativeSipBridge` methods against chosen SDK
2. Inject onto `window` before webview content runs
3. Prove dial + DTMF against lab first; then PCM `onAudio`
4. Lab dial URI from `lab/asterisk/generated/credentials.env`

**Acceptance:**
- [ ] In Tauri, `__promptpathSipBridge` is defined
- [ ] Lab Asterisk receives INVITE for extension 1000
- [ ] Matched-step DTMF advances IVR
- [ ] Bad creds / down daemon → `error` event (failure matrix)
- [ ] Browser paths unchanged

**Branch:** `cursor/desktop-sip-bridge-7a69`

---

### U2. Lab Path config + docs (parallel with U1)

**Goal:** Lab Path is desktop-automation-ready; docs describe desktop as primary (softphone+paste is legacy).

**Files:**
- `client/public/scripts/lab-account-status.json`
- `docs/lab-run.md`
- `scripts/lab-verify-flow.sh`
- Optional: `scripts/lab-desktop.sh`

**Changes:**
- Non-empty `setup.target` (lab SIP URI; document credential override)
- `speechPreferences.autoListen: true`
- Desktop-first operator steps in `docs/lab-run.md`

**Acceptance:**
- [ ] Lab Path loads with target + autoListen
- [ ] Docs no longer prescribe softphone as the automation path
- [ ] Verify script fails fast if Asterisk / API down

**Branch:** `cursor/desktop-lab-config-7a69`

---

### U3. Local STT → RunSession

**Goal:** Automated Runs consume transport audio and call `processPhrase` without paste.

**Files:**
- `client/src/stt/**` (Whisper wrapper)
- `client/src/localStt.ts`
- `client/src/transport/AudioSession.ts` (consumers)
- `client/src/components/run/RunActivePanel.tsx`

**Depends on:** U1 `onAudio` producing PCM per audio contract

**Approach:**
1. Whisper.cpp on-device (Tauri command or native addon)
2. Debounce/endpoint → `runSession.processPhrase`
3. No Web Speech when automated + bridge present
4. Manual paste remains available as escape hatch

**Acceptance:**
- [ ] Fixture/mock PCM advances engine + DTMF action
- [ ] No STT SaaS / transcript POST in client network path
- [ ] Failure matrix: Whisper down → UI error + paste still works

**Branch:** `cursor/desktop-stt-pipeline-7a69`

---

### U4. E2E verification + integration

**Goal:** One green desktop loop; merge waves; Privacy Verification passes.

**Files:**
- `scripts/lab-verify-flow.sh` (desktop assertions)
- Integration merge only otherwise

**Depends on:** U1, U2, U3

**Operator flow:**
1. `./scripts/lab.sh`
2. `npm run desktop:dev`
3. Run Lab Path
4. Assert Runs completed + callstate ingest
5. Complete Privacy Verification checklist
6. Merge: sip → lab-config → stt → verify polish into `cursor/desktop-mvp-7a69`

**Acceptance:**
- [ ] Full checklist in `docs/lab-run.md` green on Mac once
- [ ] `cd client && npm run build` green
- [ ] `cd desktop && npm run build` green on Mac
- [ ] Privacy Verification all checked

**Branch:** merge target `cursor/desktop-mvp-7a69`

---

## Privacy Verification

Required before U4 passes:

- [ ] No outbound audio streams except SIP RTP to the intended peer
- [ ] No transcript POST requests to PromptPath or third parties
- [ ] Callstate payload is encrypted blob + nonce only
- [ ] DTMF ledger stores hash (and digit **count**), never plaintext sequences
- [ ] Whisper model executes locally
- [ ] Network capture during a lab Run shows no STT egress

---

## Verification Contract

| Gate | Check |
|------|-------|
| Client TS | `cd client && npm run build` |
| Desktop | `cd desktop && npm run build` (Mac) |
| API | `curl -sf http://127.0.0.1:8000/health` |
| Lab | SIP TLS port up after `./scripts/lab.sh` |
| Bridge | `__promptpathSipBridge` present in Tauri |
| E2E | Lab Path completes; Runs shows completed |
| Privacy | Checklist above |

---

## Definition of Done

**Global**
- [ ] U0–U4 complete
- [ ] Single SIP stack locked and used
- [ ] Dial + DTMF + local STT + encrypted ingest proven on Mac lab
- [ ] Privacy Verification complete
- [ ] PR opened with wave checklist

**Per unit:** see Acceptance bullets under each U-ID.

---

## Fasttrack playbook

1. Ship U0 (agents + scout lock)
2. Wave A parallel: `desktop-sip-bridge` + `desktop-lab-e2e` (config half)
3. Freeze `docs/desktop-audio-contract.md` before STT coding starts in earnest
4. Wave B: `desktop-stt-pipeline`
5. Wave C: `desktop-integration` + full `desktop-lab-e2e` verify

```bash
cd /Users/cameroncohen/Developer/projects/PromptPath
git fetch && git checkout cursor/desktop-mvp-7a69 && git pull
./scripts/lab.sh
npm run desktop:dev
```

---

## Appendix — Baseline already done

- Thin API (token, consent link, callstate CRUD/revoke)
- Tauri scaffold + desktop-dev sidecar
- `RunSession` + `createAppTransport`
- Job-oriented UI nav
- Lab Asterisk scripts (Path still softphone-oriented today)

## Appendix — Risk register

| Risk | Mitigation |
|------|------------|
| SIP SDK build pain | Scout locks one stack; brew/deps documented |
| Whisper latency | Short windows + paste escape hatch |
| Lab TLS self-signed | Localhost trust / insecure-lab flag only |
| Agent coupling | Frozen contracts + exclusive ownership |

## Appendix — Origin refs

- `docs/architecture-boundary.md`
- `docs/roadmap.md`
- `docs/lab-run.md`
- `client/src/transport/CallTransport.ts`
- `client/src/transport/SipTransport.ts`
- `client/src/engine/runSession.ts`
