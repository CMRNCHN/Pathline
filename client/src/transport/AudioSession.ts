import type { AudioFrameHandler, CallTransport } from "./CallTransport";
import type { SttEngine, SttErrorHandler, SttPhraseHandler } from "../stt/types";

/** Routes transport audio to one or more local recognizers. */
export class AudioSession {
  private unsub?: () => void;

  constructor(private readonly transport: CallTransport) {}

  attach(handler: AudioFrameHandler): () => void {
    this.unsub?.();
    this.unsub = this.transport.onAudio(handler);
    return () => {
      this.unsub?.();
      this.unsub = undefined;
    };
  }

  detach(): void {
    this.unsub?.();
    this.unsub = undefined;
  }

  /**
   * Wire a local STT engine to the call: start the engine, forward every
   * transport `onAudio` PCM frame into `engine.pushAudio`, and deliver endpointed
   * phrases to `onPhrase` (typically `runSession.processPhrase`). Audio and
   * transcripts stay on device — nothing here is sent to the server.
   *
   * Returns a stop function that detaches the transport subscription and stops
   * the engine.
   */
  runStt(
    engine: SttEngine,
    onPhrase: SttPhraseHandler,
    onError?: SttErrorHandler
  ): () => void {
    engine.start(onPhrase, onError);
    const detach = this.attach((pcm, sampleRate) => engine.pushAudio(pcm, sampleRate));
    return () => {
      detach();
      engine.stop();
    };
  }
}
