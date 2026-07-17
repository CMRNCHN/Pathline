/**
 * On-device speech-to-text abstraction.
 *
 * Every engine consumes PCM frames delivered through the frozen
 * `CallTransport.onAudio(pcm, sampleRate)` contract
 * (see docs/desktop-audio-contract.md) and emits endpointed phrases. Audio and
 * transcripts stay on the device — no engine here may POST audio/transcripts to
 * any server or call a cloud/SaaS STT.
 */

/** Which local recognizer produced the phrases. */
export type SttSource = "local_whisper" | "web_speech" | "mock";

/** Called with an endpointed phrase ready for phrase matching. */
export type SttPhraseHandler = (phrase: string) => void;

/** Called when the engine cannot listen (model/runtime unavailable, etc.). */
export type SttErrorHandler = (message: string) => void;

/**
 * A local recognizer. The consumer (`AudioSession`) forwards transport audio via
 * `pushAudio`; the engine owns VAD / endpointing and emits complete phrases to
 * the `onPhrase` handler registered in `start`.
 *
 * Engines that capture their own audio (e.g. Web Speech, which uses the browser
 * mic) ignore `pushAudio`.
 */
export interface SttEngine {
  /** Identifies the recognizer for diagnostics / audit-free logging. */
  readonly source: SttSource;
  /** Begin listening. Phrases go to `onPhrase`; fatal issues to `onError`. */
  start(onPhrase: SttPhraseHandler, onError?: SttErrorHandler): void;
  /** Feed one raw PCM frame (mono float32, normalized to [-1, 1]). */
  pushAudio(pcm: Float32Array, sampleRate: number): void;
  /** Stop listening and release buffers. Safe to call multiple times. */
  stop(): void;
}

/** Result of probing the environment for a usable local STT engine. */
export interface SttCapability {
  /** Whether an on-device Whisper runtime is reachable. */
  localWhisperAvailable: boolean;
  /** Whether a native SIP bridge is injected (Tauri desktop shell). */
  bridgePresent: boolean;
  /** Whether the browser Web Speech API is available (dev fallback only). */
  webSpeechAvailable: boolean;
}

/** Inputs used to pick an engine and decide whether auto-listen is possible. */
export interface SttSelectionContext {
  /** True when a CallTransport is present (desktop/native or simulate flag). */
  automated: boolean;
}

/** Outcome of engine selection. */
export interface SttSelection {
  /** The chosen engine, or null when no automatic listener is available. */
  engine: SttEngine | null;
  /** The capability snapshot used to decide. */
  capability: SttCapability;
  /**
   * Populated when `engine` is null: a human-readable reason the UI can surface
   * as a listen error while keeping the manual-paste escape hatch.
   */
  unavailableReason?: string;
}
