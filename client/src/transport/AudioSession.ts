import type { AudioFrameHandler, CallTransport } from "./CallTransport";

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
}
