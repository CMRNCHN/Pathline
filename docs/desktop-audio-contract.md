# Desktop audio-frame contract (Frozen)

**Status:** Locked
**Date:** 2026-07-17
**Authority:** `docs/architecture-boundary.md`, `docs/desktop-sip-stack.md` (`LOCKED_SIP_STACK=rsiprtp`), `docs/plans/2026-07-14-desktop-sip-stt-e2e.md`

This document freezes the PCM audio-frame contract between the desktop SIP bridge
(producer) and the local STT pipeline (consumer). SIP and STT work must cite this
doc; conflicting frame formats are rejected in review.

## Frozen interface

Audio is delivered through the existing, frozen `CallTransport.onAudio` method
(`client/src/transport/CallTransport.ts`):

```ts
export type AudioFrameHandler = (pcm: Float32Array, sampleRate: number) => void;

onAudio(handler: AudioFrameHandler): () => void;
```

The same 2-argument shape is mirrored on the native bridge
(`client/src/transport/SipTransport.ts`, `NativeSipBridge.onAudio`). Do **not**
change these signatures without a plan amendment.

Shared constants live in `client/src/transport/audioFormat.ts`:

```ts
export const PREFERRED_STT_SAMPLE_RATE = 16000;
export const AUDIO_CHANNELS = 1;
export const AUDIO_SAMPLE_FORMAT = "float32";
```

## Format

- **Container:** `Float32Array` (32-bit float PCM).
- **Sample range:** normalized to `[-1.0, 1.0]`.
- **Channels:** **mono** (`AUDIO_CHANNELS = 1`). Multi-channel is not delivered
  today and must not be added by silently overloading the existing 2-arg
  signature. Any future extension requires a plan amendment and a new,
  backward-compatible channel-aware path — the mono `(pcm, sampleRate)` contract
  stays intact.

## Sample rate

- **Preferred: 16000 Hz** (`PREFERRED_STT_SAMPLE_RATE`) to match the local
  Whisper path.
- The `sampleRate` argument reports the rate of the delivered frames.
- **The SIP bridge resamples** when the negotiated codec differs. Example: G.711
  media at 8000 Hz is resampled up to 16000 Hz by the bridge before delivery.
  STT must read the provided `sampleRate` rather than assuming a fixed value, but
  the bridge should target 16000 Hz whenever practical.

## Delivery

- The transport emits **continuous** `onAudio` callbacks for the duration of the
  call — one raw PCM frame per callback, in capture order.
- `onAudio(handler)` returns an **unsubscribe function**; calling it stops
  delivery to that handler. This is the same convention used by
  `client/src/transport/AudioSession.ts`.
- **STT owns VAD / endpointing.** The transport does no voice-activity detection,
  segmentation, or silence trimming; it forwards frames as captured. Buffering,
  windowing, and endpointing are the consumer's responsibility.

## Privacy

- **No audio payloads inside transport *events*.** `TransportEvent`
  (`connected`, `disconnected`, `ringing`, `answered`, `dtmf_sent`, `error`)
  never carries PCM, transcripts, or secrets — consistent with
  `docs/architecture-boundary.md` rule 3. Audio flows only through the dedicated
  `onAudio` channel.
- **Audio never leaves the device.** PCM is produced and consumed locally and is
  not sent to the Pathline server (identity + encrypted artifact storage only).

## Producers and consumers

- **Producer:** `desktop/src-tauri/src/sip_bridge.rs` (pure-Rust `rsiprtp`
  stack), exposed to the client as `window.__pathlineSipBridge`
  (`NativeSipBridge`). It owns dial, RTP media, DTMF injection, and PCM framing,
  and must not import `RunSession`, `runEngine`, or UI.
- **Consumer:** `client/src/stt/**`, wired to the transport via
  `client/src/transport/AudioSession.ts`, which routes `onAudio` frames to the
  local recognizer(s).

## References

- Frozen transport interfaces: `client/src/transport/CallTransport.ts`,
  `client/src/transport/SipTransport.ts`
- Shared constants: `client/src/transport/audioFormat.ts`
- Architecture boundary: `docs/architecture-boundary.md`
- SIP stack decision: `docs/desktop-sip-stack.md`
