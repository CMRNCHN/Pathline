/**
 * User-facing labels for rule types and data flow.
 *
 * Direction:
 *   Listen & save  — IVR speaks → script stores a field
 *   Send when asked — you supply at run time → IVR receives it
 *   Navigate menu  — script sends keys/speech to move the IVR
 */

export const ruleTypeLabel = {
  capture: "Listen & save",
  captureListenOnly: "Listen only",
  respond: "Send when asked",
  navigate: "Navigate menu",
  end: "End the call",
} as const;

export const ruleFieldLabel = {
  /** IVR phrase that activates the rule */
  whenIvrSays: "When the IVR says",
  whenIvrAsks: "When the IVR asks",
  whenYouHear: "When you hear",
  /** Capture: name for text saved from the IVR */
  saveAs: "Save as",
  /** Respond: name for a value the caller enters before the run */
  runValue: "Run value",
  action: "Then",
} as const;

export const ruleFieldHint = {
  saveAs: "Name for what the IVR says — filled in automatically during the call.",
  runValue: "Name only in the script — you enter the real value when you start a run.",
  captureTrigger: "Words the IVR speaks before you save (e.g. “Your balance is”).",
  respondTrigger: "Words the IVR uses when it wants input (e.g. “Enter your account number”).",
  navigateTrigger: "Menu prompt that means you should press or speak next.",
} as const;

export const outputsSection = {
  title: "Outputs",
  description: "What this script expects to receive from you and save from the IVR.",
  runValues: "You provide at run time",
  savedFromIvr: "Saved from the IVR",
  empty: "Add rules to declare run values and fields saved from the IVR.",
} as const;

export const runCopy = {
  configureValues: "Values for this call",
  configureHint: "Enter the real values the IVR will ask for — stored only on your device.",
  savedDuringCall: "Saved during the call",
} as const;

export function triggerLabelForIntent(
  intent: "capture" | "navigate" | "respond" | "end" | null
): string {
  switch (intent) {
    case "capture":
      return ruleFieldLabel.whenIvrSays;
    case "respond":
      return ruleFieldLabel.whenIvrAsks;
    case "navigate":
      return ruleFieldLabel.whenYouHear;
    default:
      return "When";
  }
}
