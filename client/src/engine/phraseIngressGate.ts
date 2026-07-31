import type { PathDocument } from "@/script/types";
import { evaluateDetect } from "@/engine/when/evaluateDetect";
import { END_NOW_DETECT, NEXT_UTTERANCE_DETECT } from "@/engine/runEngine";

export interface PhraseIngressGateOptions {
  silenceAfterPromptMs: number;
  path: PathDocument;
  matchedFlowIds: () => string[];
}

/**
 * Delays phrase delivery after a match until silenceAfterPromptMs elapses,
 * mirroring ivr-tester PostSilencePrompt behaviour.
 */
export class PhraseIngressGate {
  private silenceTimer: ReturnType<typeof setTimeout> | undefined;
  private pendingPhrase: string | undefined;

  constructor(
    private readonly options: PhraseIngressGateOptions,
    private readonly deliver: (phrase: string) => Promise<void>
  ) {}

  public dispose(): void {
    this.clearTimer();
    this.pendingPhrase = undefined;
  }

  public async onPhrase(text: string): Promise<void> {
    const phrase = text.trim();
    if (!phrase) return;

    if (!this.shouldDelay(phrase)) {
      this.clearTimer();
      await this.deliver(phrase);
      return;
    }

    this.pendingPhrase = phrase;
    this.clearTimer();
    this.silenceTimer = setTimeout(() => {
      const ready = this.pendingPhrase;
      this.pendingPhrase = undefined;
      if (ready) {
        void this.deliver(ready);
      }
    }, this.options.silenceAfterPromptMs);
  }

  private shouldDelay(phrase: string): boolean {
    const matched = new Set(this.options.matchedFlowIds());
    const next = this.options.path.conversationFlow.find(
      (step) =>
        !matched.has(step.id) &&
        step.detect !== NEXT_UTTERANCE_DETECT &&
        step.detect !== END_NOW_DETECT
    );
    if (!next) return false;
    return evaluateDetect(phrase, next.detect);
  }

  private clearTimer(): void {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = undefined;
    }
  }
}
