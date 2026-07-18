/** Plain-language copy for the fixed When → Then Step shape. */

export const ruleTypeLabel = {
  capture: "Save what you hear",
  captureListenOnly: "Keep listening",
  respond: "Send an Input",
  navigate: "Press keys or speak",
  end: "End the call",
} as const;

export const ruleFieldLabel = {
  cue: "IVR says",
  when: "When",
  then: "Then",
  whenIvrSays: "Phrase to match",
  whenIvrAsks: "Phrase to match",
  whenYouHear: "Phrase to match",
  saveAs: "Save as",
  runValue: "Input",
  action: "Then",
  label: "Label",
} as const;

export const ruleFieldHint = {
  saveAs: "Name the value Pathline saves from the IVR.",
  runValue: "Name the value you enter when you start a Run.",
  captureTrigger: "The words Pathline should listen for, such as “Your balance is”.",
  respondTrigger: "The words Pathline should listen for, such as “Enter your account number”.",
  navigateTrigger: "The words that mean Pathline should act.",
} as const;

export const outputsSection = {
  title: "Outputs",
  description: "What this Workflow receives from you and saves from the IVR.",
  runValues: "You provide at run time",
  savedFromIvr: "Saved from the IVR",
  empty: "Add Steps to declare Inputs and values saved from the IVR.",
} as const;

export const runCopy = {
  configureValues: "Values for this call",
  configureHint: "Enter the real values the IVR will ask for — stored only on your device.",
  savedDuringCall: "Saved during the call",
} as const;

export function triggerLabelForIntent(
  intent: "capture" | "navigate" | "respond" | "end" | null
): string {
  return intent === "end" ? "When" : ruleFieldLabel.cue;
}
