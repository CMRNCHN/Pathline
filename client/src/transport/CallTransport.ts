/** Low-level transport events — no secrets, transcripts, or audio payloads. */
export type TransportEventType =
  | "connected"
  | "disconnected"
  | "ringing"
  | "answered"
  | "dtmf_sent"
  | "error";

export interface TransportEvent {
  type: TransportEventType;
  timestamp: string;
  detail?: string;
}

/** Raw PCM audio frames for local STT — never leaves the device via Pathline server. */
export type AudioFrameHandler = (pcm: Float32Array, sampleRate: number) => void;

export type TransportEventHandler = (event: TransportEvent) => void;

/**
 * Owns the call media session. Engine code depends on this interface only —
 * not on SIP, CallKit, PSTN, or UI.
 */
export interface CallTransport {
  dial(number: string): Promise<void>;
  answer(): Promise<void>;
  sendDTMF(digits: string, durationMs: number): Promise<void>;
  hangup(): Promise<void>;
  onAudio(handler: AudioFrameHandler): () => void;
  onEvent(handler: TransportEventHandler): () => void;
}
