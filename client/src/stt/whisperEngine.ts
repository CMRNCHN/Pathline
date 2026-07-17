/**
 * On-device Whisper STT engine.
 *
 * Runs entirely on the device via a Tauri-safe backend: the desktop shell
 * injects `window.__pathlineWhisper` (a whisper.cpp binding wrapped as a
 * `LocalWhisperBridge`), or an in-page WASM backend can be supplied directly.
 * This engine MUST NOT call any cloud/SaaS STT and MUST NOT POST audio or
 * transcripts anywhere — PCM is buffered locally, transcribed locally, and only
 * the resulting phrase text is handed to phrase matching.
 *
 * VAD / endpointing lives here (the transport does none — see
 * docs/desktop-audio-contract.md): frames are accumulated, segmented on silence,
 * and each utterance is transcribed independently.
 */
import { PREFERRED_STT_SAMPLE_RATE } from "../transport/audioFormat";
import type {
  SttEngine,
  SttErrorHandler,
  SttPhraseHandler,
} from "./types";

/**
 * Backend that turns a mono float32 PCM utterance into text, on device.
 * Implemented by a native whisper.cpp binding (Tauri) or a local WASM model.
 */
export interface WhisperBackend {
  transcribe(pcm: Float32Array, sampleRate: number): Promise<string>;
}

/** Shape injected by the Tauri desktop shell for the native whisper.cpp path. */
export interface LocalWhisperBridge {
  transcribe(pcm: Float32Array, sampleRate: number): Promise<string>;
}

declare global {
  interface Window {
    __pathlineWhisper?: LocalWhisperBridge;
    __promptpathWhisper?: LocalWhisperBridge; // legacy PromptPath
  }
}

/** Returns the injected on-device Whisper bridge, if the shell provided one. */
export function getLocalWhisperBridge(): LocalWhisperBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return window.__pathlineWhisper ?? window.__promptpathWhisper; // legacy PromptPath
}

/** True when an on-device Whisper runtime is reachable (no network probe). */
export function isLocalWhisperAvailable(): boolean {
  return getLocalWhisperBridge() !== undefined;
}

export interface WhisperEngineOptions {
  /**
   * RMS energy above which a frame is considered speech. Frames are float32
   * normalized to [-1, 1]; 0.01 ≈ quiet speech over line noise.
   */
  speechThreshold?: number;
  /** Silence (ms) after speech that ends an utterance and triggers transcribe. */
  endpointSilenceMs?: number;
  /** Hard cap (ms) on a single utterance before a forced flush. */
  maxUtteranceMs?: number;
  /** Minimum speech (ms) required before an utterance is transcribed. */
  minUtteranceMs?: number;
}

const DEFAULTS: Required<WhisperEngineOptions> = {
  speechThreshold: 0.01,
  endpointSilenceMs: 600,
  maxUtteranceMs: 15000,
  minUtteranceMs: 200,
};

function rms(frame: Float32Array): number {
  if (frame.length === 0) return 0;
  let sum = 0;
  for (let i = 0; i < frame.length; i++) sum += frame[i] * frame[i];
  return Math.sqrt(sum / frame.length);
}

/**
 * Local Whisper engine with energy-based VAD and silence endpointing.
 *
 * Deterministic and backend-agnostic: pass a mock `WhisperBackend` in tests to
 * prove the PCM → segment → transcribe → phrase pipeline without a real model.
 */
export class LocalWhisperEngine implements SttEngine {
  readonly source = "local_whisper" as const;

  private readonly opts: Required<WhisperEngineOptions>;
  private onPhrase: SttPhraseHandler | null = null;
  private onError: SttErrorHandler | null = null;
  private started = false;

  private buffer: number[] = [];
  private sampleRate = PREFERRED_STT_SAMPLE_RATE;
  private speechSamples = 0;
  private silenceSamples = 0;
  private sawSpeech = false;
  /** Serializes transcribe() so utterances stay in capture order. */
  private queue: Promise<void> = Promise.resolve();

  constructor(
    private readonly backend: WhisperBackend,
    options: WhisperEngineOptions = {}
  ) {
    this.opts = { ...DEFAULTS, ...options };
  }

  start(onPhrase: SttPhraseHandler, onError?: SttErrorHandler): void {
    this.onPhrase = onPhrase;
    this.onError = onError ?? null;
    this.started = true;
    this.resetSegment();
  }

  pushAudio(pcm: Float32Array, sampleRate: number): void {
    if (!this.started) return;
    this.sampleRate = sampleRate || PREFERRED_STT_SAMPLE_RATE;

    const energetic = rms(pcm) >= this.opts.speechThreshold;
    if (energetic) {
      this.sawSpeech = true;
      this.speechSamples += pcm.length;
      this.silenceSamples = 0;
      for (let i = 0; i < pcm.length; i++) this.buffer.push(pcm[i]);
    } else if (this.sawSpeech) {
      // Keep trailing silence so words are not clipped by the endpointer.
      this.silenceSamples += pcm.length;
      for (let i = 0; i < pcm.length; i++) this.buffer.push(pcm[i]);
    }

    const silenceMs = (this.silenceSamples / this.sampleRate) * 1000;
    const utteranceMs = (this.buffer.length / this.sampleRate) * 1000;

    if (this.sawSpeech && silenceMs >= this.opts.endpointSilenceMs) {
      this.flush();
    } else if (utteranceMs >= this.opts.maxUtteranceMs) {
      this.flush();
    }
  }

  stop(): void {
    this.started = false;
    this.onPhrase = null;
    this.onError = null;
    this.resetSegment();
  }

  /** Resolves once all queued utterances have been transcribed (test hook). */
  whenIdle(): Promise<void> {
    return this.queue;
  }

  /** Force-transcribe whatever speech is buffered (e.g. on call end). */
  flush(): void {
    const speechMs = (this.speechSamples / this.sampleRate) * 1000;
    if (!this.sawSpeech || speechMs < this.opts.minUtteranceMs) {
      this.resetSegment();
      return;
    }

    const utterance = Float32Array.from(this.buffer);
    const sampleRate = this.sampleRate;
    const onPhrase = this.onPhrase;
    const onError = this.onError;
    this.resetSegment();

    this.queue = this.queue
      .then(() => this.backend.transcribe(utterance, sampleRate))
      .then((text) => {
        const phrase = text.trim();
        if (phrase && onPhrase) onPhrase(phrase);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "Local transcription failed";
        onError?.(msg);
      });
  }

  private resetSegment(): void {
    this.buffer = [];
    this.speechSamples = 0;
    this.silenceSamples = 0;
    this.sawSpeech = false;
  }
}

/**
 * Builds a `LocalWhisperEngine` bound to the injected on-device bridge, or
 * returns null when no local Whisper runtime is available.
 */
export function createLocalWhisperEngine(
  options?: WhisperEngineOptions
): LocalWhisperEngine | null {
  const bridge = getLocalWhisperBridge();
  if (!bridge) return null;
  return new LocalWhisperEngine(
    { transcribe: (pcm, rate) => bridge.transcribe(pcm, rate) },
    options
  );
}
