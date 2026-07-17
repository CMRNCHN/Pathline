---
name: desktop-sip-harden
description: Hardens the rsiprtp SIP bridge for real-world calls — failure matrix (RTP timeout, call drop, reconnect, bad creds), symmetric-RTP/NAT behavior. Use proactively after the live lab proof.
---

You make the rsiprtp SIP bridge production-resilient.

## Preconditions
- Live lab available (see `desktop-lab-live`). Base off `origin/cursor/desktop-next-0880`.

## Owns exclusively
- `desktop/src-tauri/src/sip_bridge.rs` and its tests

## Implement (failure matrix from docs/plans/2026-07-14-desktop-sip-stt-e2e.md)
- RTP timeout / media stall / call drop -> emit `disconnected` + clean `CALL_ENDED` (abandoned); no hang.
- Bad creds / unreachable peer -> `error` event with detail (validate it already fails closed).
- Basic reconnect/retry policy for transient signaling failures.
- Symmetric RTP / learned-endpoint behavior against a non-loopback peer (real Asterisk).
- Keep DTMF audit `{ step, digits: count, hash }`; never plaintext.

## Must NOT
- Change `NativeSipBridge`/`CallTransport` signatures.
- Add C SDK/FFI (stay pure-Rust rsiprtp family).
- Import `RunSession`/`runEngine`/UI.

## Verify
- `cd desktop/src-tauri && cargo test` (add tests for timeout/drop/error paths).
- Validate against the live lab where feasible; document deferred items.
