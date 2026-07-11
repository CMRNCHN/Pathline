import type { Step } from "./types";
import { formatVariableRef } from "./compile";
import { newId } from "./storage";
import { CUSTOM_PRESET_ID } from "./rulePresets";
import { ruleTypeLabel } from "./ruleCopy";

export type RuleWizardType = "capture" | "navigate" | "respond" | "end";

export type NavigateMode = "keypad" | "speak" | "wait";
export type RespondDelivery = "keypad" | "speak";

const VAR_REF = /\{\{(\w+)\}\}/;

export interface CaptureWizardDraft {
  intent: "capture";
  infoPresetId: string;
  customOutput?: string;
  trigger: string;
  save: boolean;
  output: string;
}

export interface NavigateWizardDraft {
  intent: "navigate";
  mode: NavigateMode;
  trigger: string;
  /** Literal DTMF key or spoken text when mode is keypad/speak */
  responseLiteral: string;
  waitSeconds?: number;
}

export interface RespondWizardDraft {
  intent: "respond";
  infoPresetId: string;
  customVariable?: string;
  delivery: RespondDelivery;
  variable: string;
  trigger: string;
}

export interface EndWizardDraft {
  intent: "end";
}

export type WizardDraft =
  | CaptureWizardDraft
  | NavigateWizardDraft
  | RespondWizardDraft
  | EndWizardDraft;

/** @deprecated Use RuleWizardType */
export type RuleIntent = RuleWizardType | "wait";

/** @deprecated Use WizardDraft */
export type RuleDraft = WizardDraft;

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

function hasVariableRef(response: string): boolean {
  return VAR_REF.test(response);
}

export function inferIntent(rule: Step): RuleWizardType {
  if (rule.rule === "End call") return "end";
  if (rule.rule === "Capture value after detect" || (rule.output.trim() && rule.rule !== "Wait for IVR response")) {
    return "capture";
  }
  if (rule.rule === "Wait for IVR response") {
    if (rule.when.trim() && !rule.waitSeconds) {
      return "capture";
    }
    return "navigate";
  }
  if (
    rule.rule === "Inject DTMF after detect" ||
    rule.rule === "Inject speech after detect"
  ) {
    return hasVariableRef(rule.then) ? "respond" : "navigate";
  }
  return "navigate";
}

export function labelBaseForDraft(draft: WizardDraft): string {
  switch (draft.intent) {
    case "capture":
      return draft.save ? `capture_${slugify(draft.output || "value")}` : `listen_${slugify(draft.trigger || "phrase")}`;
    case "navigate":
      if (draft.mode === "wait") return `wait_${draft.waitSeconds ?? 3}s`;
      if (draft.mode === "keypad") return `press_${slugify(draft.responseLiteral || "key")}`;
      return `speak_${slugify(draft.responseLiteral || "phrase")}`;
    case "respond":
      return `submit_${slugify(draft.variable || "value")}`;
    case "end":
      return "end_call";
  }
}

export function buildRuleFromDraft(
  draft: WizardDraft,
  existingLabels: string[],
  existingId?: string,
  previousLabel?: string
): Step {
  const base = labelBaseForDraft(draft);
  const label = uniqueLabel(base, existingLabels, previousLabel);

  switch (draft.intent) {
    case "capture":
      if (draft.save) {
        return {
          id: existingId ?? newId(),
          label,
          when: draft.trigger.trim(),
          then: "",
          rule: "Capture value after detect",
          output: slugify(draft.output),
        };
      }
      return {
        id: existingId ?? newId(),
        label,
        when: draft.trigger.trim(),
        then: "",
        rule: "Wait for IVR response",
        output: "",
      };
    case "navigate":
      if (draft.mode === "wait") {
        return {
          id: existingId ?? newId(),
          label,
          when: "",
          then: "",
          rule: "Wait for IVR response",
          output: "",
          waitSeconds: draft.waitSeconds ?? 3,
        };
      }
      return {
        id: existingId ?? newId(),
        label,
        when: draft.trigger.trim(),
        then: draft.responseLiteral.trim(),
        rule:
          draft.mode === "keypad" ? "Inject DTMF after detect" : "Inject speech after detect",
        output: "",
      };
    case "respond":
      return {
        id: existingId ?? newId(),
        label,
        when: draft.trigger.trim(),
        then: formatVariableRef(draft.variable),
        rule:
          draft.delivery === "keypad" ? "Inject DTMF after detect" : "Inject speech after detect",
        output: "",
      };
    case "end":
      return {
        id: existingId ?? newId(),
        label,
        when: "",
        then: "",
        rule: "End call",
        output: "",
      };
  }
}

export function ruleToDraft(rule: Step): WizardDraft {
  const intent = inferIntent(rule);

  switch (intent) {
    case "capture": {
      if (rule.rule === "Wait for IVR response") {
        return {
          intent: "capture",
          infoPresetId: CUSTOM_PRESET_ID,
          trigger: rule.when,
          save: false,
          output: "",
        };
      }
      return {
        intent: "capture",
        infoPresetId: CUSTOM_PRESET_ID,
        customOutput: rule.output,
        trigger: rule.when,
        save: true,
        output: rule.output,
      };
    }
    case "navigate": {
      if (rule.rule === "Wait for IVR response") {
        return {
          intent: "navigate",
          mode: "wait",
          trigger: "",
          responseLiteral: "",
          waitSeconds: rule.waitSeconds ?? 3,
        };
      }
      const isSpeech = rule.rule === "Inject speech after detect";
      return {
        intent: "navigate",
        mode: isSpeech ? "speak" : "keypad",
        trigger: rule.when,
        responseLiteral: rule.then,
      };
    }
    case "respond": {
      const match = rule.then.match(/\{\{(\w+)\}\}/);
      return {
        intent: "respond",
        infoPresetId: CUSTOM_PRESET_ID,
        customVariable: match?.[1] ?? "",
        delivery: rule.rule === "Inject speech after detect" ? "speak" : "keypad",
        variable: match?.[1] ?? "",
        trigger: rule.when,
      };
    }
    case "end":
      return { intent: "end" };
  }
}

export function isPlaceholderRule(rule: Step): boolean {
  if (rule.rule === "End call" || rule.rule === "Wait for IVR response") {
    return rule.rule === "Wait for IVR response" && !rule.when.trim() && !rule.waitSeconds;
  }
  return !rule.when.trim() && !rule.then.trim() && !rule.output.trim();
}

export interface RuleSummary {
  typeLabel: string;
  trigger: string;
  action: string;
  inputVariable?: string;
  outputVariable?: string;
}

export function ruleSummary(rule: Step): RuleSummary {
  const intent = inferIntent(rule);
  const varMatch = rule.then.match(/\{\{(\w+)\}\}/);

  switch (intent) {
    case "capture":
      if (rule.rule === "Wait for IVR response") {
        return {
          typeLabel: ruleTypeLabel.captureListenOnly,
          trigger: rule.when,
          action: "Wait for the next IVR prompt",
        };
      }
      return {
        typeLabel: ruleTypeLabel.capture,
        trigger: rule.when,
        action: "Save what the IVR says",
        outputVariable: rule.output ? formatVariableRef(rule.output) : undefined,
      };
    case "navigate":
      if (rule.rule === "Wait for IVR response") {
        return {
          typeLabel: ruleTypeLabel.navigate,
          trigger: "—",
          action: `Wait ${rule.waitSeconds ?? 3} seconds`,
        };
      }
      return {
        typeLabel: ruleTypeLabel.navigate,
        trigger: rule.when,
        action:
          rule.rule === "Inject speech after detect"
            ? `Speak: "${rule.then}"`
            : `Press: ${rule.then}`,
      };
    case "respond":
      return {
        typeLabel: ruleTypeLabel.respond,
        trigger: rule.when,
        action:
          rule.rule === "Inject speech after detect"
            ? "Speak your run value"
            : "Send your run value (touch-tones)",
        inputVariable: varMatch ? formatVariableRef(varMatch[1]) : undefined,
      };
    case "end":
      return {
        typeLabel: ruleTypeLabel.end,
        trigger: "—",
        action: "Hang up",
      };
  }
}

export function ruleCardTitle(rule: Step): string {
  return ruleSummary(rule).typeLabel;
}

export function ruleCardAction(rule: Step): string {
  return ruleSummary(rule).action;
}

export function draftSummary(draft: WizardDraft | null): RuleSummary | null {
  if (!draft) return null;
  const rule = buildRuleFromDraft(draft, []);
  return ruleSummary(rule);
}

export function validateDraft(draft: WizardDraft | null): boolean {
  if (!draft) return false;
  switch (draft.intent) {
    case "capture":
      if (!draft.trigger.trim()) return false;
      return draft.save ? Boolean(draft.output.trim()) : true;
    case "navigate":
      if (draft.mode === "wait") return (draft.waitSeconds ?? 0) >= 1;
      return Boolean(draft.trigger.trim() && draft.responseLiteral.trim());
    case "respond":
      return Boolean(draft.trigger.trim() && draft.variable.trim());
    case "end":
      return true;
  }
}

export function truncateTrigger(trigger: string, max = 48): string {
  const t = trigger.trim();
  if (!t) return "—";
  if (t.length <= max) return `"${t}"`;
  return `"${t.slice(0, max)}…"`;
}
