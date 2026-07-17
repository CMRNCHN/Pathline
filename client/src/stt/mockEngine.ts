/**
 * Deterministic mock STT engine for fixtures / unit-style proofs.
 *
 * It does no real recognition: each `pushAudio` frame maps (in order) to a
 * scripted phrase, so a known PCM buffer flowing through
 * AudioSession → STT → runSession.processPhrase can be verified headlessly,
 * without a bundled Whisper model.
 */
import type { SttEngine, SttErrorHandler, SttPhraseHandler } from "./types";

export class MockSttEngine implements SttEngine {
  readonly source = "mock" as const;
  private onPhrase: SttPhraseHandler | null = null;
  private index = 0;

  constructor(private readonly phrases: string[]) {}

  start(onPhrase: SttPhraseHandler, _onError?: SttErrorHandler): void {
    void _onError;
    this.onPhrase = onPhrase;
    this.index = 0;
  }

  /** Each pushed frame emits the next scripted phrase, if any remain. */
  pushAudio(_pcm: Float32Array, _sampleRate: number): void {
    void _pcm;
    void _sampleRate;
    if (!this.onPhrase) return;
    const phrase = this.phrases[this.index];
    if (phrase === undefined) return;
    this.index += 1;
    this.onPhrase(phrase);
  }

  stop(): void {
    this.onPhrase = null;
    this.index = 0;
  }
}
