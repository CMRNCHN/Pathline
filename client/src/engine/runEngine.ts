import type { FlowStep, PathDocument, RunLogEntry, RunState } from "../script/types";
import { extractOutputRules, findIvrRule, resolveReference } from "../script/compile";

export type { RunState, RunLogEntry };

/** Open capture: save the next reply after prior Steps finish (no cue phrase). */
export const NEXT_UTTERANCE_DETECT = "__next_utterance__";
/** Open end: hang up once prior Steps finish (no goodbye cue). */
export const END_NOW_DETECT = "__end_now__";

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
  speechAction?: {
    step: string;
    text: string;
  };
}

export function initialRunState(): RunState {
  return { collected: {}, log: [], matchedFlowIds: [], completed: false };
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
  if (phrase === NEXT_UTTERANCE_DETECT || phrase === END_NOW_DETECT) return false;
  const hay = text.toLowerCase().replace(/\s+/g, " ").trim();
  return phrase
    .split("|")
    .map((p) => p.trim().toLowerCase())
    .filter(Boolean)
    .some((needle) => hay.includes(needle));
}

function priorsDone(flow: FlowStep[], index: number, matchedIds: Set<string>): boolean {
  return flow.slice(0, index).every((step) => matchedIds.has(step.id));
}

function findMatchingFlowStep(
  doc: PathDocument,
  phrase: string,
  matchedIds: Set<string>
): FlowStep | undefined {
  const flow = doc.conversationFlow;

  for (let index = 0; index < flow.length; index++) {
    const step = flow[index];
    if (matchedIds.has(step.id)) continue;

    if (step.detect === NEXT_UTTERANCE_DETECT || step.detect === END_NOW_DETECT) {
      if (priorsDone(flow, index, matchedIds)) return step;
      continue;
    }

    if (matches(phrase, step.detect)) return step;
  }

  return undefined;
}

function nextStepIsOpenEnd(doc: PathDocument, step: FlowStep): boolean {
  const index = doc.conversationFlow.findIndex((item) => item.id === step.id);
  if (index < 0) return false;
  const next = doc.conversationFlow[index + 1];
  return next?.action === "end" && next.detect === END_NOW_DETECT;
}

function withMatched(prev: RunState, stepId: string): string[] {
  const existing = prev.matchedFlowIds ?? [];
  return existing.includes(stepId) ? existing : [...existing, stepId];
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

  const matchedIds = new Set(prev.matchedFlowIds ?? []);
  const step = findMatchingFlowStep(doc, phrase, matchedIds);
  const base: RunState = {
    ...prev,
    lastPhrase: phrase,
    pendingDtmf: undefined,
    pendingTrigger: undefined,
    matchedFlowIds: prev.matchedFlowIds ?? [],
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

  const matchedFlowIds = withMatched(prev, step.id);

  switch (step.action) {
    case "pass": {
      return {
        state: {
          ...base,
          matchedFlowIds,
          log: [...prev.log, logEntry(`Pass: "${step.detect}"`, "pass")],
        },
        matched: true,
        shouldComplete: nextStepIsOpenEnd(doc, step),
      };
    }

    case "trigger": {
      const ivrRule = step.triggerLabel ? findIvrRule(doc, step.triggerLabel) : undefined;
      const resolved = ivrRule ? resolveReference(ivrRule.then, variables) : undefined;
      const stepName = step.triggerLabel ?? step.detect;
      const isSpeech = ivrRule?.rule === "Inject speech after detect";
      const log = [
        ...prev.log,
        logEntry(
          resolved
            ? isSpeech
              ? "Speak when asked"
              : `Send when asked → ${resolved.length} digit(s)`
            : "Send rule not found",
          "trigger"
        ),
      ];
      const shouldComplete = nextStepIsOpenEnd(doc, step);

      if (automated && resolved) {
        return {
          state: { ...base, matchedFlowIds, log },
          matched: true,
          shouldComplete,
          ...(isSpeech
            ? { speechAction: { step: stepName, text: resolved } }
            : { dtmfAction: { step: stepName, sequence: resolved } }),
        };
      }

      if (isSpeech) {
        return {
          state: {
            ...base,
            matchedFlowIds,
            log: [...log, logEntry("Speech action requires a speech-capable transport", "unknown")],
          },
          matched: true,
          shouldComplete: false,
        };
      }

      const state: RunState = {
        ...base,
        matchedFlowIds,
        log,
        pendingDtmf: resolved,
        pendingTrigger: step.detect,
      };
      return { state, matched: true, shouldComplete };
    }

    case "extract": {
      const ivrRule = step.triggerLabel ? findIvrRule(doc, step.triggerLabel) : undefined;
      const field = ivrRule?.output ?? "";
      const value = field ? phrase : "";
      const collected = value ? { ...prev.collected, [field]: value } : prev.collected;
      const openCapture = step.detect === NEXT_UTTERANCE_DETECT;
      const log = [
        ...prev.log,
        logEntry(
          value && field
            ? openCapture
              ? `Saved ${field} from next reply: ${value.slice(0, 80)}${value.length > 80 ? "…" : ""}`
              : `Saved ${field} from IVR: ${value.slice(0, 80)}${value.length > 80 ? "…" : ""}`
            : "Listen & save rule missing field name",
          value && field ? "extract" : "unknown"
        ),
      ];
      const matched = Boolean(value && field);
      return {
        state: {
          ...base,
          collected,
          log,
          matchedFlowIds: matched ? matchedFlowIds : base.matchedFlowIds,
        },
        matched,
        shouldComplete: matched && nextStepIsOpenEnd(doc, step),
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
      return {
        state: { ...base, log, matchedFlowIds: ok ? matchedFlowIds : base.matchedFlowIds },
        matched: ok,
        shouldComplete: false,
      };
    }

    case "end": {
      const log = [
        ...prev.log,
        logEntry(
          step.detect === END_NOW_DETECT ? "End call" : `End: "${step.detect}"`,
          "end"
        ),
      ];
      return {
        state: { ...base, log, matchedFlowIds, completed: true },
        matched: true,
        shouldComplete: true,
      };
    }

    default:
      return { state: prev, matched: false, shouldComplete: false };
  }
}
