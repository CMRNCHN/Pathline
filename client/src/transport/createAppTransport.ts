import type { CallTransport } from "./CallTransport";
import { createSipTransport } from "./SipTransport";

/** True when running inside the Tauri desktop shell. */
export function isTauriApp(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/**
 * Returns a CallTransport for automated runs, or null for manual browser fallback.
 * - Tauri desktop: SIP bridge when injected, else SimulatorTransport (dev)
 * - Browser dev: SimulatorTransport when VITE_SIMULATE_TRANSPORT=1
 */
export function createAppTransport(): CallTransport | null {
  if (isTauriApp()) {
    return createSipTransport();
  }

  if (import.meta.env.VITE_SIMULATE_TRANSPORT === "true") {
    return createSipTransport();
  }

  return null;
}

/** True when a CallTransport is available (desktop shell or simulate flag). */
export function isAutomatedTransport(): boolean {
  return createAppTransport() !== null;
}
