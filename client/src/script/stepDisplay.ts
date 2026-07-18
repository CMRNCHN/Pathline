import type { Step } from "./types";
import { inferIntent } from "./ruleIntent";

export interface StepDisplay {
  cue: string;
  match: string;
  action: string;
  value: string;
  label: string;
}

export function stepDisplay(step: Step): StepDisplay {
  const intent = inferIntent(step);

  if (intent === "end") {
    return {
      cue: "Workflow reaches",
      match: "this Step",
      action: "end call",
      value: "",
      label: step.label,
    };
  }

  if (intent === "capture") {
    return {
      cue: "IVR says",
      match: step.when || "any phrase",
      action: step.output ? "save" : "keep listening",
      value: step.output || "",
      label: step.label,
    };
  }

  if (step.rule === "Wait for IVR response") {
    return {
      cue: "Workflow reaches",
      match: "this Step",
      action: "wait",
      value: `${step.waitSeconds ?? 3} sec`,
      label: step.label,
    };
  }

  return {
    cue: "IVR says",
    match: step.when || "any phrase",
    action: step.rule === "Inject speech after detect" ? "speak" : "press keys",
    value: step.then,
    label: step.label,
  };
}
