import type { Step } from "../../../script/types";
import type { WizardDraft } from "../../../script/ruleIntent";
import { ruleToDraft } from "../../../script/ruleIntent";
import {
  CAPTURE_PRESETS,
  CUSTOM_PRESET_ID,
  RESPOND_PRESETS,
} from "../../../script/rulePresets";
import { firstStepForType } from "./machine";
import type { WizardState } from "./types";

export const emptyCapture = {
  presetId: "",
  output: "",
  trigger: "",
  save: true,
};

export const emptyNavigate = {
  mode: "keypad" as const,
  value: "1",
  trigger: "",
  waitSeconds: 3,
};

export const emptyRespond = {
  presetId: "",
  variable: "",
  delivery: "keypad" as const,
  trigger: "",
};

export function emptyWizardState(): WizardState {
  return {
    intent: null,
    step: "intent",
    capture: { ...emptyCapture },
    navigate: { ...emptyNavigate },
    respond: { ...emptyRespond },
  };
}

function stateFromDraft(draft: WizardDraft, openAtSummary: boolean): WizardState {
  const base: WizardState = {
    intent: draft.intent,
    step: openAtSummary ? "summary" : firstStepForType(draft.intent),
    capture: { ...emptyCapture },
    navigate: { ...emptyNavigate },
    respond: { ...emptyRespond },
  };

  switch (draft.intent) {
    case "capture": {
      const preset = CAPTURE_PRESETS.find((p) => p.outputVar === draft.output);
      return {
        ...base,
        capture: {
          presetId: preset?.id ?? CUSTOM_PRESET_ID,
          output: draft.output,
          trigger: draft.trigger,
          save: draft.save,
        },
      };
    }
    case "navigate":
      return {
        ...base,
        navigate: {
          mode: draft.mode,
          value: draft.responseLiteral,
          trigger: draft.trigger,
          waitSeconds: draft.waitSeconds ?? 3,
        },
      };
    case "respond": {
      const preset = RESPOND_PRESETS.find((p) => p.varName === draft.variable);
      return {
        ...base,
        respond: {
          presetId: preset?.id ?? CUSTOM_PRESET_ID,
          variable: draft.variable,
          delivery: draft.delivery,
          trigger: draft.trigger,
        },
      };
    }
    case "end":
      return base;
  }
}

export function initialWizardState(editingRule?: Step): WizardState {
  if (!editingRule) return emptyWizardState();
  return stateFromDraft(ruleToDraft(editingRule), true);
}

export function wizardStateFromRule(rule: Step, openAtSummary = false): WizardState {
  return stateFromDraft(ruleToDraft(rule), openAtSummary);
}
