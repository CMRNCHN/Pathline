import type { RuleWizardType } from "../../../script/ruleIntent";
import type { WizardState, WizardStep } from "./types";

export function stepLabel(step: WizardStep, intent: RuleWizardType | null): string {
  if (step === "intent") return "What should this step do?";
  if (step === "summary") return "Review Step";

  switch (intent) {
    case "capture":
      if (step.startsWith("capture-")) return "Fill in When and Then";
      break;
    case "navigate":
      if (step.startsWith("navigate-")) return "Fill in When and Then";
      break;
    case "respond":
      if (step.startsWith("respond-")) return "Fill in When and Then";
      break;
    case "end":
      break;
  }
  return "";
}

export function stepProgress(
  step: WizardStep,
  intent: RuleWizardType | null
): { current: number; total: number } {
  if (step === "intent") return { current: 1, total: 3 };
  if (step === "summary") return { current: 3, total: 3 };
  return { current: intent ? 2 : 1, total: 3 };
}

export function firstStepForType(type: RuleWizardType): WizardStep {
  switch (type) {
    case "capture":
      return "capture-info";
    case "navigate":
      return "navigate-mode";
    case "respond":
      return "respond-info";
    case "end":
      return "summary";
  }
}

export function nextStep(state: WizardState): WizardStep {
  const { step } = state;
  switch (step) {
    case "capture-info":
      return "summary";
    case "navigate-mode":
      return "summary";
    case "respond-info":
      return "summary";
    default:
      return step;
  }
}

export function backStep(state: WizardState): WizardStep {
  const { step, intent } = state;

  if (step === "summary") {
    if (intent === "end") return "intent";
    if (intent === "capture") return "capture-info";
    if (intent === "navigate") return "navigate-mode";
    if (intent === "respond") return "respond-info";
    return "intent";
  }

  return "intent";
}
