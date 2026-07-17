---
name: desktop-stt-pipeline
description: Wires local Whisper STT from CallTransport onAudio into RunSession.processPhrase for automated desktop runs. Use proactively in Wave B after SIP bridge exposes PCM and docs/desktop-audio-contract.md is frozen.
---

You connect on-device speech-to-text to Pathline automation.

## Preconditions

- `docs/desktop-audio-contract.md` present
- SIP bridge delivers `onAudio` (or use fixture PCM for unit proof while waiting)

## Owns exclusively

- `client/src/stt/**` (new)
- `client/src/localStt.ts`
- `client/src/transport/AudioSession.ts` (consumer wiring only)
- `client/src/components/run/RunActivePanel.tsx` (auto-listen for automated mode)

## Must NOT

- Edit `desktop/src-tauri/**` or SIP crate deps
- POST audio or transcripts to any server
- Change `CallTransport` signatures
- Use Web Speech when `automated && bridge present`

## Behavior

1. Attach to transport `onAudio` via `AudioSession`
2. Run Whisper.cpp (or Tauri command wrapping whisper) **locally**
3. Debounce/endpoint → `await runSession.processPhrase(text)`
4. Browser manual mode: paste + optional Web Speech fallback only
5. On Whisper unavailable: surface listen error; keep paste path

## Privacy

- No STT SaaS
- No transcript in ledger or API payloads
- Network capture of a lab Run must show no STT egress

## Workflow

```bash
cd /workspace
git checkout -b cursor/desktop-stt-pipeline-0880 origin/cursor/desktop-mvp-0880
./scripts/lab.sh
npm run desktop:dev
```

## Verify

- Fixture PCM → phrase match → DTMF action
- Automated Run does not start Web Speech
- `cd client && npm run build`

## Output

Automated lab Path can complete without paste when SIP audio is live.
