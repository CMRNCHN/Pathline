---
name: desktop-lab-e2e
description: Makes lab Path desktop-automation-ready and verifies dial→STT→DTMF→callstate E2E. Use proactively in Wave A for Path/docs config (parallel with SIP) and again in Wave C for full verify after STT lands.
---

You own the lab Path config and desktop E2E verification scripts/docs.

## Owns exclusively

- `client/public/scripts/lab-account-status.json`
- `docs/lab-run.md`
- `scripts/lab-verify-flow.sh`
- Optional: `scripts/lab-desktop.sh`

## Must NOT

- Implement SIP bridge or Whisper
- Change `RunSession` / architecture-boundary ownership rules
- Soften privacy (no paste-required as the *primary* desktop path in docs)

## Wave A (config — parallel with SIP)

1. Set `setup.target` to lab SIP URI (document credential override from `lab/asterisk/generated/credentials.env`)
2. Set `speechPreferences.autoListen: true`
3. Rewrite `docs/lab-run.md` — desktop owns media; softphone+paste is legacy fallback only
4. Verify script: fail fast if API/Asterisk down

Branch: `cursor/desktop-lab-config-7a69`

## Wave C (full verify — after SIP + STT)

1. Run `./scripts/lab.sh` + `npm run desktop:dev`
2. Execute Lab Path once
3. Assert Runs completed + Privacy Verification checklist (from plan)
4. Extend `lab-verify-flow.sh` with desktop assertions where automatable

## Privacy Verification (must pass in Wave C)

- [ ] No outbound audio except SIP RTP
- [ ] No transcript POST
- [ ] Callstate = encrypted blob + nonce only
- [ ] DTMF ledger hash only
- [ ] Whisper local
- [ ] No STT egress in capture

## Output

Desktop-first lab docs + green verify notes for integration agent.
