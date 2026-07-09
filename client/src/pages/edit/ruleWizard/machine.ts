import type { RuleWizardType } from "../../../script/ruleIntent";
import type { WizardState, WizardStep } from "./types";

export function stepLabel(step: WizardStep, intent: RuleWizardType | null): string {
  if (step === "intent") return "What should this step do?";
  if (step === "summary") return "Review rule";

  switch (intent) {
    case "capture":
      if (step === "capture-info") return "What information are you collecting?";
      if (step === "capture-trigger") return "How do you know the IVR is providing this?";
      if (step === "capture-save") return "Should we save this value?";
      break;
    case "navigate":
      if (step === "navigate-mode") return "How should we navigate?";
      if (step === "navigate-action") return "What should the assistant do?";
      if (step === "navigate-trigger") return "What tells us to perform this action?";
      break;
    case "respond":
      if (step === "respond-info") return "What information does the IVR need?";
      if (step === "respond-delivery") return "How should it be provided?";
      if (step === "respond-variable") return "Which variable does the IVR need?";
      if (step === "respond-trigger") return "What tells us the IVR is asking?";
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
  if (step === "intent") return { current: 1, total: 1 };
  if (step === "summary") {
    const totals: Record<RuleWizardType, number> = {
      capture: 5,
      navigate: 5,
      respond: 6,
      end: 2,
    };
    return { current: intent ? totals[intent] : 1, total: intent ? totals[intent] : 1 };
  }

  const captureSteps: WizardStep[] = ["capture-info", "capture-trigger", "capture-save", "summary"];
  const navigateSteps: WizardStep[] = ["navigate-mode", "navigate-action", "navigate-trigger", "summary"];
  const respondSteps: WizardStep[] = [
    "respond-info",
    "respond-delivery",
    "respond-variable",
    "respond-trigger",
    "summary",
  ];

  if (intent === "capture") {
    return { current: captureSteps.indexOf(step) + 2, total: 5 };
  }
  if (intent === "navigate") {
    if (step === "navigate-action") return { current: 3, total: 5 };
    return { current: navigateSteps.indexOf(step) + 2, total: 5 };
  }
  if (intent === "respond") {
    return { current: respondSteps.indexOf(step) + 2, total: 6 };
  }
  return { current: 1, total: 1 };
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
  const { step, navigate } = state;
  switch (step) {
    case "capture-info":
      return "capture-trigger";
    case "capture-trigger":
      return "capture-save";
    case "capture-save":
      return "summary";
    case "navigate-mode":
      return "navigate-action";
    case "navigate-action":
      return navigate.mode === "wait" ? "summary" : "navigate-trigger";
    case "navigate-trigger":
      return "summary";
    case "respond-info":
      return "respond-delivery";
    case "respond-delivery":
      return "respond-variable";
    case "respond-variable":
      return "respond-trigger";
    case "respond-trigger":
      return "summary";
    default:
      return step;
  }
}

export function backStep(state: WizardState): WizardStep {
  const { step, intent, navigate } = state;

  if (step === "summary") {
    if (intent === "end") return "intent";
    if (intent === "capture") return "capture-save";
    if (intent === "navigate") {
      return navigate.mode === "wait" ? "navigate-action" : "navigate-trigger";
    }
    if (intent === "respond") return "respond-trigger";
    return "intent";
  }

  switch (step) {
    case "capture-save":
      return "capture-trigger";
    case "capture-trigger":
      return "capture-info";
    case "capture-info":
      return "intent";
    case "navigate-trigger":
      return "navigate-action";
    case "navigate-action":
      return "navigate-mode";
    case "navigate-mode":
      return "intent";
    case "respond-trigger":
      return "respond-variable";
    case "respond-variable":
      return "respond-delivery";
    case "respond-delivery":
      return "respond-info";
    case "respond-info":
      return "intent";
    default:
      return "intent";
  }
}
