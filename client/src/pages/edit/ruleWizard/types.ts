import type { Dispatch } from "react";
import type { NavigateMode, RespondDelivery, RuleWizardType } from "../../../script/ruleIntent";

export type WizardStep =
  | "intent"
  | "capture-info"
  | "capture-trigger"
  | "capture-save"
  | "navigate-mode"
  | "navigate-action"
  | "navigate-trigger"
  | "respond-info"
  | "respond-delivery"
  | "respond-variable"
  | "respond-trigger"
  | "summary";

export interface CaptureState {
  presetId: string;
  output: string;
  trigger: string;
  save: boolean;
}

export interface NavigateState {
  mode: NavigateMode;
  value: string;
  trigger: string;
  waitSeconds: number;
}

export interface RespondState {
  presetId: string;
  variable: string;
  delivery: RespondDelivery;
  trigger: string;
}

export interface WizardState {
  intent: RuleWizardType | null;
  step: WizardStep;
  capture: CaptureState;
  navigate: NavigateState;
  respond: RespondState;
}

export type WizardAction =
  | { type: "LOAD_RULE"; state: WizardState }
  | { type: "SET_INTENT"; intent: RuleWizardType }
  | { type: "SET_CAPTURE_PRESET"; presetId: string; output?: string; trigger?: string }
  | { type: "SET_CAPTURE_TRIGGER"; trigger: string }
  | { type: "SET_CAPTURE_OUTPUT"; output: string }
  | { type: "SET_CAPTURE_SAVE"; save: boolean }
  | { type: "SET_NAVIGATE_MODE"; mode: NavigateMode }
  | { type: "SET_NAVIGATE_VALUE"; value: string }
  | { type: "SET_NAVIGATE_TRIGGER"; trigger: string }
  | { type: "SET_NAVIGATE_WAIT_SECONDS"; waitSeconds: number }
  | { type: "SET_RESPOND_PRESET"; presetId: string; variable?: string; trigger?: string }
  | { type: "SET_RESPOND_VARIABLE"; variable: string }
  | { type: "SET_RESPOND_DELIVERY"; delivery: RespondDelivery }
  | { type: "SET_RESPOND_TRIGGER"; trigger: string }
  | { type: "NEXT" }
  | { type: "BACK" }
  | { type: "RESET" }
  | { type: "GO_TO_STEP"; step: WizardStep };

export interface StepProps {
  state: WizardState;
  dispatch: Dispatch<WizardAction>;
}
