import type { Step } from "./types";
import { newId } from "./storage";

export const INLINE_STEP_ACTIONS = [
  "press-keys",
  "speak",
  "save-response",
  "keep-listening",
  "wait",
  "end-call",
] as const;

export type InlineStepAction = (typeof INLINE_STEP_ACTIONS)[number];

export interface InlineStepDraft {
  when: string;
  action: InlineStepAction | "";
  value: string;
  output: string;
  waitSeconds: number;
}

export interface InlineStepValidation {
  valid: boolean;
  errors: string[];
}

const VARIABLE_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
const VARIABLE_REF = /\{\{[A-Za-z_][A-Za-z0-9_]*\}\}/g;

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function uniqueLabel(base: string, existing: string[], skip?: string): string {
  const taken = new Set(existing.filter((label) => label !== skip));
  if (!taken.has(base)) return base;
  let suffix = 2;
  while (taken.has(`${base}_${suffix}`)) suffix += 1;
  return `${base}_${suffix}`;
}

function actionForStep(step: Step): InlineStepAction | "" {
  switch (step.rule) {
    case "Inject DTMF after detect":
      return "press-keys";
    case "Inject speech after detect":
      return "speak";
    case "Capture value after detect":
      return "save-response";
    case "Wait for IVR response":
      return step.waitSeconds ? "wait" : "keep-listening";
    case "End call":
      return "end-call";
    default:
      return "";
  }
}

export function inlineDraftFromStep(step: Step): InlineStepDraft {
  const action = actionForStep(step);
  return {
    when: step.when,
    action,
    value: action === "press-keys" || action === "speak" ? step.then : "",
    output: action === "save-response" ? step.output : "",
    waitSeconds: action === "wait" ? step.waitSeconds ?? 3 : 3,
  };
}

export function emptyInlineStepDraft(): InlineStepDraft {
  return {
    when: "",
    action: "press-keys",
    value: "",
    output: "",
    waitSeconds: 3,
  };
}

function labelBaseForDraft(draft: InlineStepDraft): string {
  switch (draft.action) {
    case "press-keys":
      return `press_${slugify(draft.value || "keys")}`;
    case "speak":
      return `speak_${slugify(draft.value || "response")}`;
    case "save-response":
      return `capture_${slugify(draft.output || "response")}`;
    case "keep-listening":
      return `listen_${slugify(draft.when || "phrase")}`;
    case "wait":
      return `wait_${draft.waitSeconds}s`;
    case "end-call":
      return "end_call";
    default:
      return "step";
  }
}

export function validateInlineStepDraft(draft: InlineStepDraft): InlineStepValidation {
  const errors: string[] = [];

  if (!draft.action) errors.push("Choose an action.");
  // Save response may omit a cue: Pathline saves the next reply after prior Steps.
  // Wait / End call already allow an optional phrase.
  if (
    draft.action !== "wait" &&
    draft.action !== "end-call" &&
    draft.action !== "save-response" &&
    !draft.when.trim()
  ) {
    errors.push("Enter the phrase Pathline should listen for.");
  }

  if (draft.action === "press-keys") {
    const valueWithoutRefs = draft.value.replace(VARIABLE_REF, "");
    if (!draft.value.trim()) {
      errors.push("Enter the keys to press.");
    } else if (!/^[0-9#*]*$/.test(valueWithoutRefs) || draft.value.includes("{{{")) {
      errors.push("Keys can contain digits, #, *, and Input references such as {{pin}}.");
    }
  }

  if (draft.action === "speak" && !draft.value.trim()) {
    errors.push("Enter what Pathline should say.");
  }

  if (draft.action === "save-response") {
    if (!draft.output.trim()) {
      errors.push("Enter a name for the saved response.");
    } else if (!VARIABLE_NAME.test(draft.output.trim())) {
      errors.push("Response names must start with a letter or underscore and use only letters, numbers, and underscores.");
    }
  }

  if (
    draft.action === "wait" &&
    (!Number.isFinite(draft.waitSeconds) || draft.waitSeconds < 1 || draft.waitSeconds > 120)
  ) {
    errors.push("Choose a wait from 1 to 120 seconds.");
  }

  return { valid: errors.length === 0, errors };
}

export function buildStepFromInlineDraft(
  draft: InlineStepDraft,
  existingLabels: string[],
  existingStep?: Step
): Step {
  const validation = validateInlineStepDraft(draft);
  if (!validation.valid || !draft.action) {
    throw new Error(validation.errors[0] ?? "Step is invalid.");
  }

  const label = existingStep?.label.trim()
    ? existingStep.label
    : uniqueLabel(labelBaseForDraft(draft), existingLabels);
  const common = {
    id: existingStep?.id ?? newId(),
    label,
    when: draft.when.trim(),
    then: "",
    output: "",
  };

  switch (draft.action) {
    case "press-keys":
      return { ...common, then: draft.value.trim(), rule: "Inject DTMF after detect" };
    case "speak":
      return { ...common, then: draft.value.trim(), rule: "Inject speech after detect" };
    case "save-response":
      return { ...common, output: draft.output.trim(), rule: "Capture value after detect" };
    case "keep-listening":
      return { ...common, rule: "Wait for IVR response" };
    case "wait":
      return {
        ...common,
        rule: "Wait for IVR response",
        waitSeconds: draft.waitSeconds,
      };
    case "end-call":
      return { ...common, rule: "End call" };
  }
}

export function isStepValid(step: Step): boolean {
  return validateInlineStepDraft(inlineDraftFromStep(step)).valid;
}

export function isPlaceholderRule(step: Step): boolean {
  if (step.rule === "End call") return false;
  if (step.rule === "Wait for IVR response") {
    return !step.when.trim() && !step.waitSeconds;
  }
  return !step.when.trim() && !step.then.trim() && !step.output.trim();
}

export type RuleIntent = "capture" | "navigate" | "respond" | "end";

export function inferIntent(step: Step): RuleIntent {
  const action = actionForStep(step);
  if (action === "end-call") return "end";
  if (action === "save-response" || action === "keep-listening") return "capture";
  if (
    (action === "press-keys" || action === "speak") &&
    /\{\{[A-Za-z_][A-Za-z0-9_]*\}\}/.test(step.then)
  ) {
    return "respond";
  }
  return "navigate";
}
