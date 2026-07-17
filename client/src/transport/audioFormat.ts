/**
 * Shared PCM audio-frame constants for the SIP bridge <-> local STT contract.
 *
 * Frozen by docs/desktop-audio-contract.md. These describe the frame format
 * delivered via CallTransport.onAudio(pcm: Float32Array, sampleRate: number).
 * Pure constants only — no engine/UI imports, no behavior.
 */

/** Preferred sample rate (Hz) for the local Whisper STT path. */
export const PREFERRED_STT_SAMPLE_RATE = 16000;

/** Channel count for delivered PCM frames. Mono until explicitly extended. */
export const AUDIO_CHANNELS = 1;

/** PCM sample container: 32-bit float, samples normalized to [-1.0, 1.0]. */
export const AUDIO_SAMPLE_FORMAT = "float32" as const;
