import type { CallTransport } from "./CallTransport";
import { SimulatorTransport } from "./SimulatorTransport";

/** Bridge injected by Tauri/native shell (PJSIP / Linphone SDK). */
export interface NativeSipBridge {
  dial(number: string): Promise<void>;
  answer(): Promise<void>;
  sendDtmf(digits: string, durationMs: number): Promise<void>;
  hangup(): Promise<void>;
  onAudio(callback: (pcm: Float32Array, sampleRate: number) => void): () => void;
  onEvent(callback: (type: string, detail?: string) => void): () => void;
}

declare global {
  interface Window {
    __pathlineSipBridge?: NativeSipBridge;
    __promptpathSipBridge?: NativeSipBridge; // legacy PromptPath
  }
}

function getNativeSipBridge(): NativeSipBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return window.__pathlineSipBridge ?? window.__promptpathSipBridge; // legacy PromptPath
}

function wrapBridge(bridge: NativeSipBridge): CallTransport {
  return {
    dial: (number) => bridge.dial(number),
    answer: () => bridge.answer(),
    sendDTMF: (digits, durationMs) => bridge.sendDtmf(digits, durationMs),
    hangup: () => bridge.hangup(),
    onAudio: (handler) => bridge.onAudio(handler),
    onEvent: (handler) =>
      bridge.onEvent((type, detail) =>
        handler({
          type: type as "connected" | "disconnected" | "ringing" | "answered" | "dtmf_sent" | "error",
          timestamp: new Date().toISOString(),
          detail,
        })
      ),
  };
}

/**
 * Production SIP transport. Uses native bridge when present (Tauri desktop client);
 * falls back to SimulatorTransport in web-only dev.
 */
export function createSipTransport(): CallTransport {
  const bridge = getNativeSipBridge();
  if (bridge) return wrapBridge(bridge);
  return new SimulatorTransport();
}

export class SipTransport implements CallTransport {
  private inner = createSipTransport();

  dial(number: string): Promise<void> {
    return this.inner.dial(number);
  }

  answer(): Promise<void> {
    return this.inner.answer();
  }

  sendDTMF(digits: string, durationMs: number): Promise<void> {
    return this.inner.sendDTMF(digits, durationMs);
  }

  hangup(): Promise<void> {
    return this.inner.hangup();
  }

  onAudio(handler: (pcm: Float32Array, sampleRate: number) => void): () => void {
    return this.inner.onAudio(handler);
  }

  onEvent(handler: (event: import("./CallTransport").TransportEvent) => void): () => void {
    return this.inner.onEvent(handler);
  }
}
