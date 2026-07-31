import type { FlowStep, PathDocument, RunLogEntry, RunState } from "../script/types";
import { extractOutputRules, findIvrRule, resolveReference } from "../script/compile";
import { evaluateDetect } from "./when/evaluateDetect";

export type { RunState, RunLogEntry };

/** Open capture: save the next reply after prior Steps finish (no cue phrase). */
export const NEXT_UTTERANCE_DETECT = "__next_utterance__";
/** Open end: hang up once prior Steps finish (no goodbye cue). */
export const END_NOW_DETECT = "__end_now__";
/** Wait step token emitted by script sync for "wait N seconds" Steps. */
export const WAIT_DETECT_RE = /^__wait_(\d+(?:\.\d+)?)__$/;
const DEFAULT_STEP_TIMEOUT_MS = 30_000;

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
  timedOutStep?: {
    step: string;
    timeoutMs: number;
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
  if (
    phrase === NEXT_UTTERANCE_DETECT ||
    phrase === END_NOW_DETECT ||
    isWaitDetect(phrase)
  ) {
    return false;
  }
  const hay = text.toLowerCase().replace(/\s+/g, " ").trim();
  return evaluateDetect(hay, phrase);
}

export function isWaitDetect(detect: string): boolean {
  return WAIT_DETECT_RE.test(detect.trim());
}

export function waitMsFromDetect(detect: string): number | null {
  const match = detect.trim().match(WAIT_DETECT_RE);
  if (!match) return null;
  const seconds = Number.parseFloat(match[1]);
  if (!Number.isFinite(seconds) || seconds < 0) return null;
  return Math.round(seconds * 1000);
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

    if (isWaitDetect(step.detect)) {
      if (phrase === step.detect && priorsDone(flow, index, matchedIds)) return step;
      continue;
    }

    if (step.detect === NEXT_UTTERANCE_DETECT || step.detect === END_NOW_DETECT) {
      if (priorsDone(flow, index, matchedIds)) return step;
      continue;
    }

    if (matches(phrase, step.detect)) return step;
  }

  return undefined;
}

export function getPendingFlowStep(
  doc: PathDocument,
  prev: Pick<RunState, "matchedFlowIds" | "completed">
): FlowStep | undefined {
  if (prev.completed) return undefined;
  const matchedIds = new Set(prev.matchedFlowIds ?? []);
  return doc.conversationFlow.find((step, index) => {
    if (matchedIds.has(step.id)) return false;
    return priorsDone(doc.conversationFlow, index, matchedIds);
  });
}

function stepLabel(doc: PathDocument, step: FlowStep): string {
  if (step.triggerLabel) return step.triggerLabel;
  const index = doc.conversationFlow.findIndex((item) => item.id === step.id);
  return index >= 0 ? `#${index + 1} ${step.detect}` : step.detect;
}

export function stepTimeoutMs(doc: PathDocument, step: FlowStep): number {
  const fromRule =
    step.triggerLabel != null
      ? doc.steps.find((item) => item.label === step.triggerLabel)?.timeoutMs
      : undefined;
  const raw = step.timeoutMs ?? fromRule ?? doc.setup.timeoutMs ?? DEFAULT_STEP_TIMEOUT_MS;
  return Math.max(1_000, raw);
}

export function completeWaitStep(
  doc: PathDocument,
  prev: RunState,
  stepId?: string
): ProcessPhraseResult {
  if (prev.completed) return { state: prev, matched: false, shouldComplete: false };
  const pending = getPendingFlowStep(doc, prev);
  const step =
    stepId != null
      ? doc.conversationFlow.find((item) => item.id === stepId && item.id === pending?.id)
      : pending;
  const waitMs = step ? waitMsFromDetect(step.detect) : null;
  if (!step || waitMs == null) {
    return { state: prev, matched: false, shouldComplete: false };
  }

  const matchedFlowIds = withMatched(prev, step.id);
  const viaEnd = completeViaOpenEnd(matchedFlowIds, openEndAfter(doc, step));
  const seconds = waitMs / 1000;
  return {
    state: {
      ...prev,
      pendingDtmf: undefined,
      pendingTrigger: undefined,
      matchedFlowIds: viaEnd.matchedFlowIds,
      completed: viaEnd.completed,
      log: [...prev.log, logEntry(`Waited ${seconds} second(s)`, "pass")],
    },
    matched: true,
    shouldComplete: viaEnd.shouldComplete,
  };
}

export function timeoutPendingStep(
  doc: PathDocument,
  prev: RunState,
  stepId?: string
): ProcessPhraseResult {
  if (prev.completed) return { state: prev, matched: false, shouldComplete: false };
  const pending = getPendingFlowStep(doc, prev);
  const step =
    stepId != null
      ? doc.conversationFlow.find((item) => item.id === stepId && item.id === pending?.id)
      : pending;
  if (!step) return { state: prev, matched: false, shouldComplete: false };

  const timeoutMs = stepTimeoutMs(doc, step);
  const label = stepLabel(doc, step);
  const message = `Timed out waiting for Step "${label}" after ${timeoutMs} ms`;
  return {
    state: {
      ...prev,
      pendingDtmf: undefined,
      pendingTrigger: undefined,
      log: [...prev.log, logEntry(message, "unknown")],
    },
    matched: false,
    shouldComplete: false,
    timedOutStep: { step: label, timeoutMs },
  };
}

/** When the Step after `step` is open end, return it so callers can complete without another utterance. */
function openEndAfter(doc: PathDocument, step: FlowStep): FlowStep | undefined {
  const index = doc.conversationFlow.findIndex((item) => item.id === step.id);
  if (index < 0) return undefined;
  const next = doc.conversationFlow[index + 1];
  if (next?.action === "end" && next.detect === END_NOW_DETECT) return next;
  return undefined;
}

function withMatched(prev: Pick<RunState, "matchedFlowIds">, stepId: string): string[] {
  const existing = prev.matchedFlowIds ?? [];
  return existing.includes(stepId) ? existing : [...existing, stepId];
}

/** Mark open-end as matched and complete — disconnect finalizer keys off state.completed. */
function completeViaOpenEnd(
  matchedFlowIds: string[],
  openEnd: FlowStep | undefined
): Pick<RunState, "matchedFlowIds" | "completed"> & { shouldComplete: boolean } {
  if (!openEnd) {
    return { matchedFlowIds, completed: false, shouldComplete: false };
  }
  return {
    matchedFlowIds: withMatched({ matchedFlowIds }, openEnd.id),
    completed: true,
    shouldComplete: true,
  };
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
  if (phrase === prev.lastPhrase && !isWaitDetect(phrase)) {
    return { state: prev, matched: false, shouldComplete: false };
  }

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
      const viaEnd = completeViaOpenEnd(matchedFlowIds, openEndAfter(doc, step));
      const waitMs = waitMsFromDetect(step.detect);
      return {
        state: {
          ...base,
          matchedFlowIds: viaEnd.matchedFlowIds,
          completed: viaEnd.completed,
          log: [
            ...prev.log,
            logEntry(
              waitMs == null ? `Pass: "${step.detect}"` : `Waited ${waitMs / 1000} second(s)`,
              "pass"
            ),
          ],
        },
        matched: true,
        shouldComplete: viaEnd.shouldComplete,
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
      const viaEnd = completeViaOpenEnd(matchedFlowIds, openEndAfter(doc, step));

      if (automated && resolved) {
        return {
          state: {
            ...base,
            matchedFlowIds: viaEnd.matchedFlowIds,
            completed: viaEnd.completed,
            log,
          },
          matched: true,
          shouldComplete: viaEnd.shouldComplete,
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
        matchedFlowIds: viaEnd.matchedFlowIds,
        completed: viaEnd.completed,
        log,
        pendingDtmf: resolved,
        pendingTrigger: step.detect,
      };
      return { state, matched: true, shouldComplete: viaEnd.shouldComplete };
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
      const viaEnd = matched
        ? completeViaOpenEnd(matchedFlowIds, openEndAfter(doc, step))
        : { matchedFlowIds: base.matchedFlowIds, completed: false, shouldComplete: false };
      return {
        state: {
          ...base,
          collected,
          log,
          matchedFlowIds: viaEnd.matchedFlowIds,
          completed: viaEnd.completed,
        },
        matched,
        shouldComplete: viaEnd.shouldComplete,
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
