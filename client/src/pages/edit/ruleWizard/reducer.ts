import { findCapturePreset, findRespondPreset } from "../../../script/rulePresets";
import { firstStepForType, backStep, nextStep } from "./machine";
import { emptyWizardState } from "./state";
import type { WizardAction, WizardState } from "./types";

export function wizardReducer(state: WizardState, action: WizardAction): WizardState {
  switch (action.type) {
    case "LOAD_RULE":
      return action.state;

    case "SET_INTENT":
      return {
        ...state,
        intent: action.intent,
        step: action.intent === "end" ? "summary" : firstStepForType(action.intent),
      };

    case "SET_CAPTURE_PRESET": {
      const preset = findCapturePreset(action.presetId);
      return {
        ...state,
        capture: {
          ...state.capture,
          presetId: action.presetId,
          output: action.output ?? preset?.outputVar ?? state.capture.output,
          trigger: action.trigger ?? (state.capture.trigger || preset?.triggerHint || ""),
        },
      };
    }

    case "SET_CAPTURE_TRIGGER":
      return { ...state, capture: { ...state.capture, trigger: action.trigger } };

    case "SET_CAPTURE_OUTPUT":
      return { ...state, capture: { ...state.capture, output: action.output } };

    case "SET_CAPTURE_SAVE":
      return { ...state, capture: { ...state.capture, save: action.save } };

    case "SET_NAVIGATE_MODE":
      return { ...state, navigate: { ...state.navigate, mode: action.mode } };

    case "SET_NAVIGATE_VALUE":
      return { ...state, navigate: { ...state.navigate, value: action.value } };

    case "SET_NAVIGATE_TRIGGER":
      return { ...state, navigate: { ...state.navigate, trigger: action.trigger } };

    case "SET_NAVIGATE_WAIT_SECONDS":
      return { ...state, navigate: { ...state.navigate, waitSeconds: action.waitSeconds } };

    case "SET_RESPOND_PRESET": {
      const preset = findRespondPreset(action.presetId);
      return {
        ...state,
        respond: {
          ...state.respond,
          presetId: action.presetId,
          variable: action.variable ?? preset?.varName ?? state.respond.variable,
          trigger: action.trigger ?? (state.respond.trigger || preset?.triggerHint || ""),
        },
      };
    }

    case "SET_RESPOND_VARIABLE":
      return { ...state, respond: { ...state.respond, variable: action.variable } };

    case "SET_RESPOND_DELIVERY":
      return { ...state, respond: { ...state.respond, delivery: action.delivery } };

    case "SET_RESPOND_TRIGGER":
      return { ...state, respond: { ...state.respond, trigger: action.trigger } };

    case "SET_LABEL":
      return { ...state, label: action.label };

    case "NEXT":
      return { ...state, step: nextStep(state) };

    case "BACK":
      return { ...state, step: backStep(state) };

    case "RESET":
      return emptyWizardState();

    case "GO_TO_STEP":
      return { ...state, step: action.step };

    default:
      return state;
  }
}
