import type { ScriptDocument, RunLogEntry, RunState } from "./types";
import {
  applyExtractMap,
  findIvrRule,
  resolveReference,
} from "./compile";

export type { RunState, RunLogEntry };

export interface ProcessPhraseResult {
  state: RunState;
  matched: boolean;
  shouldComplete: boolean;
}

export function initialRunState(): RunState {
  return { collected: {}, log: [], completed: false };
}

export async function hashCollected(collected: Record<string, string>): Promise<string> {
  const data = new TextEncoder().encode(JSON.stringify(collected));
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}

function logEntry(message: string, kind: RunLogEntry["kind"]): RunLogEntry {
  return { at: new Date().toISOString(), message, kind };
}

function matches(text: string, phrase: string): boolean {
  if (!phrase.trim()) return false;
  const hay = text.toLowerCase().replace(/\s+/g, " ").trim();
  return phrase
    .split("|")
    .map((p) => p.trim().toLowerCase())
    .filter(Boolean)
    .some((needle) => hay.includes(needle));
}

function findMatchingFlowStep(doc: ScriptDocument, phrase: string) {
  return doc.conversationFlow.find((step) => matches(phrase, step.detect));
}

export function processPhrase(
  text: string,
  doc: ScriptDocument,
  variables: Record<string, string>,
  prev: RunState
): ProcessPhraseResult {
  if (prev.completed) return { state: prev, matched: false, shouldComplete: false };

  const phrase = text.trim();
  if (!phrase) return { state: prev, matched: false, shouldComplete: false };
  if (phrase === prev.lastPhrase) return { state: prev, matched: false, shouldComplete: false };

  const step = findMatchingFlowStep(doc, phrase);
  const base: RunState = {
    ...prev,
    lastPhrase: phrase,
    pendingDtmf: undefined,
    pendingTrigger: undefined,
  };

  if (!step) {
    return {
      state: {
        ...base,
        log: [
          ...prev.log,
          logEntry(`No match: "${phrase.slice(0, 60)}${phrase.length > 60 ? "…" : ""}"`, "unknown"),
        ],
      },
      matched: false,
      shouldComplete: false,
    };
  }

  switch (step.action) {
    case "pass": {
      return {
        state: {
          ...base,
          log: [...prev.log, logEntry(`Pass: "${step.detect}"`, "pass")],
        },
        matched: true,
        shouldComplete: false,
      };
    }

    case "trigger": {
      const ivrRule = step.triggerLabel ? findIvrRule(doc, step.triggerLabel) : undefined;
      const resolved = ivrRule
        ? resolveReference(ivrRule.valueReference, variables)
        : undefined;
      const log = [
        ...prev.log,
        logEntry(
          resolved
            ? `Trigger ${step.triggerLabel} → SEND ${resolved}`
            : `Trigger ${step.triggerLabel ?? "?"} — rule not found`,
          "trigger"
        ),
      ];
      const state: RunState = {
        ...base,
        log,
        pendingDtmf: resolved,
        pendingTrigger: step.detect,
      };
      return { state, matched: true, shouldComplete: false };
    }

    case "extract": {
      const field = step.extractField ?? "";
      const mapped = step.map?.length ? applyExtractMap(phrase, step.map) : undefined;
      const value = mapped ?? "";
      const collected = value ? { ...prev.collected, [field]: value } : prev.collected;
      const log = [
        ...prev.log,
        logEntry(
          value ? `Extract ${field} = ${value}` : `Extract ${field} — no map match`,
          value ? "extract" : "unknown"
        ),
      ];
      return {
        state: { ...base, collected, log },
        matched: Boolean(value),
        shouldComplete: false,
      };
    }

    case "end": {
      const log = [...prev.log, logEntry(`End: "${step.detect}"`, "end")];
      return {
        state: { ...base, log, completed: true },
        matched: true,
        shouldComplete: true,
      };
    }

    default:
      return { state: prev, matched: false, shouldComplete: false };
  }
}
