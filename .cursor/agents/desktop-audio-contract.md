---
name: desktop-audio-contract
description: Freezes PCM audio frame contract between SIP bridge and STT (sample rate, mono float32). Use proactively in Wave A after SIP scout lock — STT must not invent alternate frame formats.
---

You freeze the shared audio contract so SIP and STT agents cannot drift.

## Mission

Publish a short freeze doc (+ optional TS constants) matching existing `CallTransport.onAudio(pcm, sampleRate)`.

## Owns exclusively

- `docs/desktop-audio-contract.md`
- `client/src/transport/audioFormat.ts` (optional constants only)

## Must NOT

- Implement Whisper or SIP
- Change `CallTransport` method signatures without plan amendment
- Edit `RunSession` / lab Path

## Required defaults

- Mono float32 PCM
- Prefer **16000 Hz** for Whisper path (bridge resamples if SDK differs)
- Unsubscribe function from `onAudio`
- No audio payloads in transport *events*

## Workflow

```bash
git checkout -b cursor/desktop-audio-contract-7a69 origin/cursor/desktop-mvp-7a69
```

1. Read `client/src/transport/CallTransport.ts` + `SipTransport.ts`
2. Write `docs/desktop-audio-contract.md`
3. Optionally add `audioFormat.ts` with `PREFERRED_STT_SAMPLE_RATE = 16000`
4. Commit + push

## Output

STT and SIP agents cite this doc; conflicting frame formats are rejected in review.
