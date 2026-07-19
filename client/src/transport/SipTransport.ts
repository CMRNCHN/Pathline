import type {
  CallTransport,
  TransportEvent,
  TransportEventType,
  TransportReadiness,
} from "./CallTransport";
import { SimulatorTransport } from "./SimulatorTransport";
import { getLocalWhisperBridge } from "../stt/whisperEngine";

/** Bridge injected by Tauri/native shell (PJSIP / Linphone SDK). */
export interface NativeSipBridge {
  readiness(): Promise<{
    ready: boolean;
    signaling: string;
    media: string;
    certificate_verification: boolean;
    reason?: string;
  }>;
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

const VALID_EVENTS = new Set<TransportEventType>([
  "connected",
  "disconnected",
  "ringing",
  "answered",
  "dtmf_sent",
  "error",
]);

async function nativeReadiness(): Promise<TransportReadiness> {
  const sip = getNativeSipBridge();
  if (!sip?.readiness) {
    return {
      ready: false,
      mode: "native",
      label: "Pathline desktop",
      reason: "Native SIP readiness diagnostics are unavailable.",
    };
  }
  const whisper = getLocalWhisperBridge();
  if (!whisper?.readiness) {
    return {
      ready: false,
      mode: "native",
      label: "Pathline desktop",
      reason: "Native Whisper bridge is unavailable.",
    };
  }

  try {
    const [sipResult, whisperResult] = await Promise.all([
      sip.readiness(),
      whisper.readiness(),
    ]);
    return {
      ready: sipResult.ready && whisperResult.ready,
      mode: "native",
      label: "Pathline desktop",
      reason: sipResult.reason ?? whisperResult.reason,
    };
  } catch (error) {
    return {
      ready: false,
      mode: "native",
      label: "Pathline desktop",
      reason: error instanceof Error ? error.message : "Native Whisper initialization failed.",
    };
  }
}

function wrapBridge(bridge: NativeSipBridge): CallTransport {
  return {
    mode: "native",
    getReadiness: nativeReadiness,
    dial: (number) => bridge.dial(number),
    answer: () => bridge.answer(),
    sendDTMF: (digits, durationMs) => bridge.sendDtmf(digits, durationMs),
    hangup: () => bridge.hangup(),
    onAudio: (handler) => bridge.onAudio(handler),
    onEvent: (handler) =>
      bridge.onEvent((type, detail) => {
        if (!VALID_EVENTS.has(type as TransportEventType)) return;
        handler({
          type: type as TransportEventType,
          timestamp: new Date().toISOString(),
          detail,
        });
      }),
  };
}

/**
 * Builds a SIP transport. Native is required unless the caller explicitly opts
 * into the development simulator.
 */
export function createSipTransport(options: { allowSimulator?: boolean } = {}): CallTransport | null {
  const bridge = getNativeSipBridge();
  if (bridge) return wrapBridge(bridge);
  return options.allowSimulator ? new SimulatorTransport() : null;
}

export class SipTransport implements CallTransport {
  readonly mode;
  private readonly inner: CallTransport;

  constructor(options: { allowSimulator?: boolean } = {}) {
    const inner = createSipTransport(options);
    if (!inner) throw new Error("Native SIP bridge unavailable");
    this.inner = inner;
    this.mode = inner.mode;
  }

  getReadiness(): Promise<TransportReadiness> {
    return this.inner.getReadiness();
  }

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

  onEvent(handler: (event: TransportEvent) => void): () => void {
    return this.inner.onEvent(handler);
  }
}
