/**
 * Browser Web Speech adapter — DEV FALLBACK ONLY.
 *
 * Web Speech uses the browser's own microphone, so it ignores transport
 * `pushAudio`. It is only selected in web-only development when no native SIP
 * bridge is present. It MUST NOT be used for automated runs backed by the SIP
 * bridge (see `createSttEngine`), which use `LocalWhisperEngine` instead.
 */
import { startContinuousRecognition } from "../localStt";
import type { SttEngine, SttErrorHandler, SttPhraseHandler } from "./types";

export class WebSpeechSttEngine implements SttEngine {
  readonly source = "web_speech" as const;
  private stopFn: (() => void) | null = null;

  start(onPhrase: SttPhraseHandler, onError?: SttErrorHandler): void {
    const stop = startContinuousRecognition(
      (phrase) => onPhrase(phrase),
      (msg) => onError?.(msg)
    );
    if (!stop) {
      onError?.("Web Speech API unavailable");
      return;
    }
    this.stopFn = stop;
  }

  // Web Speech captures its own audio; transport frames are not used.
  pushAudio(): void {}

  stop(): void {
    this.stopFn?.();
    this.stopFn = null;
  }
}
