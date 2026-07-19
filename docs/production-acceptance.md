# Production acceptance gates

Pathline v1 ships as a native desktop automation endpoint plus a thin opaque
API. Use this checklist after CI is green.

## Automated gates (CI / `scripts/ci-verify.sh`)

- [x] Client type-check + production build
- [x] Vitest coverage for inline Step conversion and speech/DTMF dispatch
- [x] STT fixture (PCM → phrase match → DTMF, no transcript in ledger)
- [x] FastAPI authorization, retention, revocation, CORS, bounds, rate limits
- [x] Alembic migration to head
- [x] Rust SIP/Whisper unit tests with checksummed bundled model
- [x] Static lab dialplan + desktop fail-closed assertions

## Lab acceptance

Automated (CI / operator host with Docker Asterisk):

1. [x] `bash scripts/lab-verify-flow.sh` — loaded dialplan + authenticated
   SIP/TLS IVR traversal to remote BYE

Interactive desktop (operator GUI):

1. `./scripts/lab-desktop.sh` (sets `PATHLINE_SIP_PROFILE=lab`)
2. Run **Lab account status (Asterisk 1000)** end-to-end:
   dial `1000` → SIP/TLS → RTP → local Whisper → RFC 4733 keypad → remote BYE →
   encrypted `POST /v1/callstate` → local History `completed`
3. Capture traffic during the run and confirm no STT/transcript egress
4. Fault cases: missing model, bad SIP credentials, Asterisk down, API down,
   dropped RTP, early BYE

## External blockers (cannot be completed without operator assets)

| Gate | Status | Why |
|------|--------|-----|
| Production SIP trunk with SRTP | Blocked | Locked `rsiprtp 0.4.1` has no SRTP; production dialing fails closed unless `PATHLINE_SIP_PROFILE=lab` on loopback |
| Apple Developer ID signing + notarization | Blocked | Requires Apple Developer credentials not present in the repo |
| Clean-machine signed install / updater / rollback | Blocked | Depends on signed release artifacts |
| Carrier DTMF / NAT interoperability proof | Blocked | Requires a selected production trunk and credentials |

## Release packaging expectations

- Release builds inject `PATHLINE_API_URL` (HTTPS origin). Relative `/api` is
  browser-dev only.
- Bundled resources must include the pinned Whisper model + checksum manifest.
- CSP is enabled in `desktop/src-tauri/tauri.conf.json`.
- Local Run History uses macOS Keychain-backed AES-GCM storage.
- Signing command (operator-run, not CI):

```bash
# After `npm run desktop:build` produces a DMG:
codesign --deep --force --options runtime \
  --sign "Developer ID Application: <Team>" \
  path/to/Pathline.app
xcrun notarytool submit path/to/Pathline.dmg --keychain-profile pathline-notary --wait
```
