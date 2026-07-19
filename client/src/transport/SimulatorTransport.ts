import type {
  AudioFrameHandler,
  CallTransport,
  TransportEvent,
  TransportEventHandler,
} from "./CallTransport";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

/** Dev/test transport — proves engine wiring without SIP. */
export class SimulatorTransport implements CallTransport {
  readonly mode = "simulator" as const;
  private audioHandlers = new Set<AudioFrameHandler>();
  private eventHandlers = new Set<TransportEventHandler>();
  private connected = false;

  private emit(event: Omit<TransportEvent, "timestamp">): void {
    const full: TransportEvent = { ...event, timestamp: new Date().toISOString() };
    for (const handler of this.eventHandlers) handler(full);
  }

  async getReadiness() {
    return {
      ready: true,
      mode: this.mode,
      label: "Development simulator — no real call",
    } as const;
  }

  async dial(number: string): Promise<void> {
    this.emit({ type: "ringing", detail: number });
    await sleep(300);
    this.connected = true;
    this.emit({ type: "connected", detail: number });
    this.emit({ type: "answered" });
  }

  async answer(): Promise<void> {
    if (!this.connected) {
      this.connected = true;
      this.emit({ type: "answered" });
    }
  }

  async sendDTMF(digits: string, durationMs: number): Promise<void> {
    await sleep(durationMs);
    this.emit({ type: "dtmf_sent", detail: digits });
  }

  async hangup(): Promise<void> {
    this.connected = false;
    this.emit({ type: "disconnected" });
  }

  onAudio(handler: AudioFrameHandler): () => void {
    this.audioHandlers.add(handler);
    return () => this.audioHandlers.delete(handler);
  }

  onEvent(handler: TransportEventHandler): () => void {
    this.eventHandlers.add(handler);
    return () => this.eventHandlers.delete(handler);
  }
}
