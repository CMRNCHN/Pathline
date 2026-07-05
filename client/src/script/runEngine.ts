import type { StatusRule } from "./types";
import { matchIvrPhrase } from "./matcher";

export interface RunLogEntry {
  at: string;
  message: string;
  kind: "send" | "status" | "unknown" | "info";
}

export interface RunState {
  collected: Record<string, string>;
  log: RunLogEntry[];
  lastPhrase?: string;
  pendingDtmf?: string;
  pendingTrigger?: string;
  completed: boolean;
}

export function initialRunState(): RunState {
  return { collected: {}, log: [], completed: false };
}

export interface ProcessPhraseResult {
  state: RunState;
  matched: boolean;
  shouldComplete: boolean;
}

export async function hashCollected(collected: Record<string, string>): Promise<string> {
  const data = new TextEncoder().encode(JSON.stringify(collected));
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}

function logEntry(message: string, kind: RunLogEntry["kind"]): RunLogEntry {
  return { at: new Date().toISOString(), message, kind };
}

export function processPhrase(
  text: string,
  rules: StatusRule[],
  secrets: Record<string, string>,
  prev: RunState
): ProcessPhraseResult {
  if (prev.completed) return { state: prev, matched: false, shouldComplete: false };

  const phrase = text.trim();
  if (!phrase) return { state: prev, matched: false, shouldComplete: false };
  if (phrase === prev.lastPhrase) return { state: prev, matched: false, shouldComplete: false };

  const result = matchIvrPhrase(phrase, rules, secrets);
  const base = { ...prev, lastPhrase: phrase, pendingDtmf: undefined, pendingTrigger: undefined };

  if (result.type === "trigger") {
    const { rule, dtmf } = result;
    const log = [...prev.log, logEntry(
      dtmf ? `SEND ${dtmf} (heard: ${rule.trigger})` : `Heard trigger, no DTMF configured`,
      "send"
    )];
    const state: RunState = {
      ...base,
      log,
      pendingDtmf: dtmf,
      pendingTrigger: rule.trigger,
    };
    if (rule.endCall) {
      return { state: { ...state, completed: true }, matched: true, shouldComplete: true };
    }
    return { state, matched: true, shouldComplete: false };
  }

  if (result.type === "status") {
    const { rule } = result;
    const collected = { ...prev.collected, [rule.key]: rule.status };
    const log = [
      ...prev.log,
      logEntry(`${rule.key}: ${rule.status}${rule.endCall ? " ✓ END" : ""}`, "status"),
    ];
    const state: RunState = {
      ...base,
      collected,
      log,
      completed: Boolean(rule.endCall),
    };
    return { state, matched: true, shouldComplete: Boolean(rule.endCall) };
  }

  return {
    state: {
      ...base,
      log: [...prev.log, logEntry(`No match: "${phrase.slice(0, 60)}${phrase.length > 60 ? "…" : ""}"`, "unknown")],
    },
    matched: false,
    shouldComplete: false,
  };
}
