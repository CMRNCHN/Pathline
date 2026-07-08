import type { IvrRule } from "./types";
import { formatVariableRef } from "./compile";
import { newId } from "./storage";

export type RuleIntent = "navigate" | "capture" | "wait" | "end";
export type NavigateMode = "keypad" | "speak";

export interface NavigateDraft {
  intent: "navigate";
  trigger: string;
  mode: NavigateMode;
  variable: string;
}

export interface CaptureDraft {
  intent: "capture";
  trigger: string;
  output: string;
}

export interface WaitDraft {
  intent: "wait";
  waitSeconds: number;
}

export interface EndDraft {
  intent: "end";
}

export type RuleDraft = NavigateDraft | CaptureDraft | WaitDraft | EndDraft;

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function uniqueLabel(base: string, existing: string[], skip?: string): string {
  const taken = new Set(existing.filter((l) => l !== skip));
  if (!taken.has(base)) return base;
  let n = 2;
  while (taken.has(`${base}_${n}`)) n += 1;
  return `${base}_${n}`;
}

export function labelBaseForDraft(draft: RuleDraft): string {
  switch (draft.intent) {
    case "navigate":
      return `submit_${slugify(draft.variable || "value")}`;
    case "capture":
      return `capture_${slugify(draft.output || "value")}`;
    case "wait":
      return `wait_${draft.waitSeconds}s`;
    case "end":
      return "end_call";
  }
}

export function buildRuleFromDraft(
  draft: RuleDraft,
  existingLabels: string[],
  existingId?: string,
  previousLabel?: string
): IvrRule {
  const base = labelBaseForDraft(draft);
  const label = uniqueLabel(base, existingLabels, previousLabel);

  switch (draft.intent) {
    case "navigate":
      return {
        id: existingId ?? newId(),
        label,
        trigger: draft.trigger.trim(),
        response: formatVariableRef(draft.variable),
        rule:
          draft.mode === "keypad" ? "Inject DTMF after detect" : "Inject speech after detect",
        output: "",
      };
    case "capture":
      return {
        id: existingId ?? newId(),
        label,
        trigger: draft.trigger.trim(),
        response: "",
        rule: "Capture value after detect",
        output: slugify(draft.output),
      };
    case "wait":
      return {
        id: existingId ?? newId(),
        label,
        trigger: "",
        response: "",
        rule: "Wait for IVR response",
        output: "",
        waitSeconds: draft.waitSeconds,
      };
    case "end":
      return {
        id: existingId ?? newId(),
        label,
        trigger: "",
        response: "",
        rule: "End call",
        output: "",
      };
  }
}

export function inferIntent(rule: IvrRule): RuleIntent {
  if (rule.rule === "End call") return "end";
  if (rule.rule === "Wait for IVR response") return "wait";
  if (rule.rule === "Capture value after detect" || rule.output.trim()) return "capture";
  return "navigate";
}

export function ruleToDraft(rule: IvrRule): RuleDraft {
  const intent = inferIntent(rule);
  switch (intent) {
    case "navigate": {
      const match = rule.response.match(/\{\{(\w+)\}\}/);
      return {
        intent: "navigate",
        trigger: rule.trigger,
        mode: rule.rule === "Inject speech after detect" ? "speak" : "keypad",
        variable: match?.[1] ?? "",
      };
    }
    case "capture":
      return { intent: "capture", trigger: rule.trigger, output: rule.output };
    case "wait":
      return { intent: "wait", waitSeconds: rule.waitSeconds ?? 3 };
    case "end":
      return { intent: "end" };
  }
}

function humanizeToken(token: string): string {
  return token
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function ruleCardTitle(rule: IvrRule): string {
  const intent = inferIntent(rule);
  switch (intent) {
    case "navigate": {
      const match = rule.response.match(/\{\{(\w+)\}\}/);
      return `Submit ${humanizeToken(match?.[1] ?? "value")}`;
    }
    case "capture":
      return `Capture ${humanizeToken(rule.output || "information")}`;
    case "wait":
      return `Wait ${rule.waitSeconds ?? 3} seconds`;
    case "end":
      return "End the call";
  }
}

export function ruleCardAction(rule: IvrRule): string {
  const intent = inferIntent(rule);
  switch (intent) {
    case "navigate":
      return rule.rule === "Inject speech after detect" ? "Speak" : "Press keypad";
    case "capture":
      return "Capture";
    case "wait":
      return "Wait";
    case "end":
      return "End call";
  }
}

export function truncateTrigger(trigger: string, max = 48): string {
  const t = trigger.trim();
  if (!t) return "—";
  if (t.length <= max) return `"${t}"`;
  return `"${t.slice(0, max)}…"`;
}
