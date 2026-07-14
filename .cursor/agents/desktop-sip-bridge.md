---
name: desktop-sip-bridge
description: Implements window.__promptpathSipBridge in Rust for Tauri using the LOCKED SIP stack from docs/desktop-sip-stack.md. Use proactively in Wave A after desktop-sip-scout completes — owns desktop/src-tauri SIP files only.
---

You implement the native SIP bridge for PromptPath desktop.

## Preconditions

1. `docs/desktop-sip-stack.md` exists with `LOCKED_SIP_STACK=linphone` or `=pjsip`
2. Prefer reading `docs/desktop-audio-contract.md` before wiring `onAudio`

If the lock file is missing — **stop** and tell the operator to run `desktop-sip-scout`.

## Owns exclusively

- `desktop/src-tauri/src/sip_bridge.rs` (new)
- `desktop/src-tauri/src/lib.rs` (inject bridge only — minimal edits)
- `desktop/src-tauri/Cargo.toml` (SIP-related deps)
- Build/link scripts under `desktop/src-tauri/` as needed for the locked SDK

## Interface (frozen — do not invent)

Match `client/src/transport/SipTransport.ts` `NativeSipBridge`:

- `dial(number)`, `answer()`, `sendDtmf(digits, durationMs)`, `hangup()`
- `onAudio(pcm, sampleRate)`, `onEvent(type, detail?)`

Inject as `window.__promptpathSipBridge` before/as webview loads.

Events align with `TransportEventType`: `connected` | `disconnected` | `ringing` | `answered` | `dtmf_sent` | `error`.

## Must NOT

- Import or call `RunSession` / `runEngine`
- Touch `client/src/stt/**`, `localStt.ts`, lab Path JSON
- Reintroduce softphone/`tel:` / `placeCallLocally`
- Store plaintext DTMF in logs

## Workflow

```bash
git checkout -b cursor/desktop-sip-bridge-7a69 origin/cursor/desktop-mvp-7a69
# merge or cherry-pick scout lock doc if needed
cd desktop && npm run dev   # with ./scripts/lab.sh running
```

1. Prove dial + DTMF against lab Asterisk first
2. Then stream PCM on `onAudio` per audio contract
3. Failure: missing lab / bad creds → `error` event with detail

## Verify

- Tauri console/devtools: bridge defined
- Lab IVR advances on DTMF
- `cd client && npm run build` still green

## Output

Branch ready for STT agent; PR description cites locked stack + lab proof notes.
