/**
 * On-device STT engine selection.
 *
 * Selection rules (privacy-first — audio/transcripts never leave the device):
 *  1. If an on-device Whisper runtime is available, always prefer it.
 *  2. Else, when `automated && bridgePresent`, DO NOT fall back to Web Speech —
 *     surface a listen error and let the UI keep the manual-paste escape hatch.
 *  3. Else (web-only dev, no native bridge), use Web Speech if available.
 */
import { isSpeechRecognitionAvailable } from "../localStt";
import { WebSpeechSttEngine } from "./webSpeechEngine";
import {
  createLocalWhisperEngine,
  isLocalWhisperAvailable,
  type WhisperEngineOptions,
} from "./whisperEngine";
import type { SttCapability, SttSelection, SttSelectionContext } from "./types";

/** True when the Tauri desktop shell injected a native SIP bridge. */
export function isSipBridgePresent(): boolean {
  if (typeof window === "undefined") return false;
  return Boolean(window.__pathlineSipBridge ?? window.__promptpathSipBridge);
}

/** Probe the environment for local STT capabilities (no network access). */
export function detectSttCapability(): SttCapability {
  return {
    localWhisperAvailable: isLocalWhisperAvailable(),
    bridgePresent: isSipBridgePresent(),
    webSpeechAvailable: isSpeechRecognitionAvailable(),
  };
}

export interface CreateSttEngineOptions {
  whisper?: WhisperEngineOptions;
}

/**
 * Chooses the best available on-device engine for the given run context.
 * Returns `{ engine: null, unavailableReason }` when no automatic listener is
 * possible so the caller can show a listen error and keep manual paste.
 */
export function createSttEngine(
  context: SttSelectionContext,
  options: CreateSttEngineOptions = {}
): SttSelection {
  const capability = detectSttCapability();

  if (capability.localWhisperAvailable) {
    const engine = createLocalWhisperEngine(options.whisper);
    if (engine) return { engine, capability };
  }

  // Never use Web Speech for a bridge-backed automated run.
  if (context.automated && capability.bridgePresent) {
    return {
      engine: null,
      capability,
      unavailableReason:
        "On-device Whisper model unavailable — paste IVR phrases below to continue.",
    };
  }

  if (capability.webSpeechAvailable) {
    return { engine: new WebSpeechSttEngine(), capability };
  }

  return {
    engine: null,
    capability,
    unavailableReason: "No on-device speech recognition available — enter phrases manually.",
  };
}

export type {
  SttCapability,
  SttEngine,
  SttErrorHandler,
  SttPhraseHandler,
  SttSelection,
  SttSelectionContext,
  SttSource,
} from "./types";
export { LocalWhisperEngine, createLocalWhisperEngine, isLocalWhisperAvailable } from "./whisperEngine";
export type { LocalWhisperBridge, WhisperBackend, WhisperEngineOptions } from "./whisperEngine";
export { WebSpeechSttEngine } from "./webSpeechEngine";
export { MockSttEngine } from "./mockEngine";
