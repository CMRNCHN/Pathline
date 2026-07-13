import type { PathDocument, RunLogEntry, RunState } from "../script/types";
import { extractOutputRules, findIvrRule, resolveReference } from "../script/compile";

export type { RunState, RunLogEntry };

export interface ProcessPhraseOptions {
  /** When true, DTMF actions are returned for transport injection instead of pending UI state. */
  automated?: boolean;
}

export interface ProcessPhraseResult {
  state: RunState;
  matched: boolean;
  shouldComplete: boolean;
  dtmfAction?: {
    step: string;
    sequence: string;
  };
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

function findMatchingFlowStep(doc: PathDocument, phrase: string) {
  return doc.conversationFlow.find((step) => matches(phrase, step.detect));
}

/** Authority for Path execution — step state, phrase matching, and next action. */
export function processPhrase(
  text: string,
  doc: PathDocument,
  variables: Record<string, string>,
  prev: RunState,
  options: ProcessPhraseOptions = {}
): ProcessPhraseResult {
  const automated = options.automated ?? false;

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
      const resolved = ivrRule ? resolveReference(ivrRule.then, variables) : undefined;
      const stepName = step.triggerLabel ?? step.detect;
      const log = [
        ...prev.log,
        logEntry(
          resolved ? `Send when asked → ${resolved.length} digit(s)` : "Send rule not found",
          "trigger"
        ),
      ];

      if (automated && resolved) {
        return {
          state: { ...base, log },
          matched: true,
          shouldComplete: false,
          dtmfAction: { step: stepName, sequence: resolved },
        };
      }

      const state: RunState = {
        ...base,
        log,
        pendingDtmf: resolved,
        pendingTrigger: step.detect,
      };
      return { state, matched: true, shouldComplete: false };
    }

    case "extract": {
      const ivrRule = step.triggerLabel ? findIvrRule(doc, step.triggerLabel) : undefined;
      const field = ivrRule?.output ?? "";
      const value = field ? phrase : "";
      const collected = value ? { ...prev.collected, [field]: value } : prev.collected;
      const log = [
        ...prev.log,
        logEntry(
          value && field
            ? `Saved ${field} from IVR: ${value.slice(0, 80)}${value.length > 80 ? "…" : ""}`
            : "Listen & save rule missing field name",
          value && field ? "extract" : "unknown"
        ),
      ];
      return {
        state: { ...base, collected, log },
        matched: Boolean(value && field),
        shouldComplete: false,
      };
    }

    case "validate": {
      const outputs = extractOutputRules(doc).map((r) => r.output);
      const missing = outputs.filter((k) => !prev.collected[k]?.trim());
      const ok = missing.length === 0;
      const log = [
        ...prev.log,
        logEntry(
          ok ? "Validate — all outputs captured" : `Validate — missing: ${missing.join(", ")}`,
          ok ? "validate" : "unknown"
        ),
      ];
      return { state: { ...base, log }, matched: ok, shouldComplete: false };
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
