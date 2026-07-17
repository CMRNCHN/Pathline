---
name: desktop-secrets-keychain
description: Stores run secrets in the OS keychain (macOS Keychain / Linux libsecret) via a Tauri command so the desktop honors the secure-enclave privacy clause. Use proactively as a stretch hardening wave.
---

You keep desktop secrets in the OS keychain, never in plaintext or on the server.

## Preconditions
- Base off `origin/cursor/desktop-next-0880`.

## Owns exclusively
- `desktop/src-tauri/src/secrets.rs` (new) + `lib.rs` command registration (minimal)
- `desktop/src-tauri/Cargo.toml` (keychain dep, e.g. `keyring`)
- A minimal client hook to read/write secrets via the command (only if a clean seam exists)

## Requirements (from client-native/README.md)
- Secrets stored in OS keychain (Keychain / libsecret); never sent to Pathline servers, never logged.
- Scoped per run/session; cleared on revoke/delete.
- Graceful fallback + clear error if the keychain is unavailable.

## Must NOT
- Change the thin-API contract or `CallTransport`/`NativeSipBridge` signatures.
- Persist plaintext secrets to disk or ledger.

## Verify
- `cd desktop/src-tauri && cargo check`/`cargo test`.
- `cd client && npm run build` green. Document macOS-vs-Linux keychain behavior.
