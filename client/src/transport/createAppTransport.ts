import type { CallTransport } from "./CallTransport";
import { createSipTransport } from "./SipTransport";

class UnavailableDesktopTransport implements CallTransport {
  readonly mode = "native" as const;

  async getReadiness() {
    return {
      ready: false,
      mode: this.mode,
      label: "Pathline desktop",
      reason: "Native SIP bridge is unavailable. Automated Runs are blocked.",
    } as const;
  }

  async dial(): Promise<void> {
    throw new Error("Native SIP bridge is unavailable");
  }
  async answer(): Promise<void> {
    throw new Error("Native SIP bridge is unavailable");
  }
  async sendDTMF(): Promise<void> {
    throw new Error("Native SIP bridge is unavailable");
  }
  async hangup(): Promise<void> {}
  onAudio(): () => void {
    return () => {};
  }
  onEvent(): () => void {
    return () => {};
  }
}

/** True when running inside the Tauri desktop shell. */
export function isTauriApp(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/**
 * Returns a CallTransport for automated runs, or null for manual browser fallback.
 * - Tauri desktop: native SIP only; a missing bridge fails closed.
 * - Browser dev: simulator only with the explicit VITE_SIMULATE_TRANSPORT=true flag.
 */
export function createAppTransport(): CallTransport | null {
  if (isTauriApp()) {
    return createSipTransport() ?? new UnavailableDesktopTransport();
  }

  if (import.meta.env.VITE_SIMULATE_TRANSPORT === "true") {
    return createSipTransport({ allowSimulator: true });
  }

  return null;
}

/** True when a CallTransport is available (desktop shell or simulate flag). */
export function isAutomatedTransport(): boolean {
  return createAppTransport() !== null;
}
