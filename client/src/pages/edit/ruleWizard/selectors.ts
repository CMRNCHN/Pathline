import type {
  CaptureWizardDraft,
  NavigateWizardDraft,
  RespondWizardDraft,
  WizardDraft,
} from "../../../script/ruleIntent";
import {
  buildRuleFromDraft,
  draftSummary,
  uniqueLabel,
  validateDraft,
} from "../../../script/ruleIntent";
import { CUSTOM_PRESET_ID, findRespondPreset } from "../../../script/rulePresets";
import type { WizardState, WizardStep } from "./types";

export function selectDraft(state: WizardState): WizardDraft | null {
  if (!state.intent) return null;

  switch (state.intent) {
    case "capture": {
      const { capture } = state;
      const draft: CaptureWizardDraft = {
        intent: "capture",
        infoPresetId: capture.presetId,
        trigger: capture.trigger,
        save: capture.save,
        output: capture.save ? capture.output.trim() : "",
      };
      return draft;
    }
    case "navigate": {
      const { navigate } = state;
      const draft: NavigateWizardDraft = {
        intent: "navigate",
        mode: navigate.mode,
        trigger: navigate.trigger,
        responseLiteral: navigate.value,
        waitSeconds: navigate.waitSeconds,
      };
      return draft;
    }
    case "respond": {
      const { respond } = state;
      const variable =
        respond.presetId === CUSTOM_PRESET_ID
          ? respond.variable
          : findRespondPreset(respond.presetId)?.varName ?? respond.variable;
      const draft: RespondWizardDraft = {
        intent: "respond",
        infoPresetId: respond.presetId,
        delivery: respond.delivery,
        variable,
        trigger: respond.trigger,
      };
      return draft;
    }
    case "end":
      return { intent: "end" };
  }
}

export function selectSummary(state: WizardState) {
  return draftSummary(selectDraft(state));
}

export function selectCanSave(state: WizardState): boolean {
  return validateDraft(selectDraft(state));
}

export function canProceedFromStep(state: WizardState): boolean {
  const { step, capture, navigate, respond } = state;
  switch (step) {
    case "capture-info":
      return Boolean(
        capture.presetId &&
          capture.trigger.trim() &&
          (!capture.save || capture.output.trim())
      );
    case "capture-trigger":
      return Boolean(capture.trigger.trim());
    case "capture-save":
      return capture.save ? Boolean(capture.output.trim()) : true;
    case "navigate-mode":
      return navigate.mode === "wait"
        ? navigate.waitSeconds >= 1
        : Boolean(navigate.trigger.trim() && navigate.value.trim());
    case "navigate-action":
      if (navigate.mode === "wait") return navigate.waitSeconds >= 1;
      return Boolean(navigate.value.trim());
    case "navigate-trigger":
      return Boolean(navigate.trigger.trim());
    case "respond-info":
      return Boolean(respond.presetId && respond.variable.trim() && respond.trigger.trim());
    case "respond-delivery":
      return true;
    case "respond-variable":
      return Boolean(respond.variable.trim());
    case "respond-trigger":
      return Boolean(respond.trigger.trim());
    case "summary":
      return selectCanSave(state);
    default:
      return false;
  }
}

export function buildRuleFromState(
  state: WizardState,
  existingLabels: string[],
  existingId?: string,
  previousLabel?: string
) {
  const draft = selectDraft(state);
  if (!draft) throw new Error("No draft");
  const step = buildRuleFromDraft(draft, existingLabels, existingId, previousLabel);
  const customLabel = state.label.trim();
  return customLabel
    ? { ...step, label: uniqueLabel(customLabel, existingLabels, previousLabel) }
    : step;
}

export function summaryEditStep(state: WizardState, field: "trigger" | "action" | "input" | "output"): WizardStep | null {
  const { intent } = state;
  if (!intent) return null;

  switch (field) {
    case "trigger":
      if (intent === "capture") return "capture-trigger";
      if (intent === "navigate") return "navigate-trigger";
      if (intent === "respond") return "respond-trigger";
      return null;
    case "action":
      if (intent === "capture") return "capture-save";
      if (intent === "navigate") return "navigate-action";
      if (intent === "respond") return "respond-delivery";
      return null;
    case "input":
      if (intent === "respond") return "respond-variable";
      return null;
    case "output":
      if (intent === "capture") return "capture-save";
      return null;
    default:
      return null;
  }
}
