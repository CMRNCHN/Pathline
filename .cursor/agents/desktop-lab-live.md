---
name: desktop-lab-live
description: Stands up the Docker lab Asterisk + API and proves the rsiprtp SIP bridge dials extension 1000 live via a headless integration test. Use proactively to validate step 2 (live SIP loop) without the Tauri GUI.
---

You prove the desktop SIP loop against a live lab, headlessly.

## Preconditions
- `desktop/src-tauri/src/sip_bridge.rs` exists (rsiprtp; `LOCKED_SIP_STACK=rsiprtp`).
- Base off `origin/cursor/desktop-next-0880`.

## Owns exclusively
- `desktop/src-tauri/tests/**` (new integration tests)
- `scripts/lab-live-test.sh` (new)

## Workflow
1. Install Docker (docker-in-docker) if absent; generate lab TLS creds via `scripts/lab-sip-setup.sh`.
2. Bring up Asterisk: `docker compose --profile lab up -d asterisk`; start the API (`scripts/dev.sh`).
3. Confirm SIP/TLS port 5061 open + API `/health` ok.
4. Add a headless Rust integration test that drives the `sip_bridge.rs` dial path against the live
   lab: INVITE ext 1000 over TLS -> answer -> send RFC 4733 DTMF -> receive RTP -> decode PCM.
   Assert transport events (`ringing`/`connected`/`answered`/`dtmf_sent`) and that PCM frames arrive.
5. Run it; report honestly how far the live handshake gets.

## Must NOT
- Change frozen `sip_bridge.rs` public behavior or `NativeSipBridge`/`CallTransport` signatures
  (test-only `#[cfg(test)]` hooks are OK).
- Implement Whisper or edit client engine/UI code.

## Verify
- `cd desktop/src-tauri && cargo test` (report live-test result vs. unit tests).
- Document proven-here vs. deferred (Tauri GUI Run stays a macOS-host task; no display here).
