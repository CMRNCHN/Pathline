import type { RuleWizardType } from "../../../../script/ruleIntent";
import type { StepProps } from "../types";

const INTENTS: { value: RuleWizardType; label: string; hint: string }[] = [
  {
    value: "capture",
    label: "Listen & save",
    hint: "The IVR speaks → you save what it said",
  },
  {
    value: "navigate",
    label: "Navigate menu",
    hint: "Press keys or speak to move through the IVR",
  },
  {
    value: "respond",
    label: "Send when asked",
    hint: "The IVR asks → you send a value from the run",
  },
  { value: "end", label: "End the call", hint: "Hang up when this step runs" },
];

export function IntentStep({ dispatch }: StepProps) {
  return (
    <div className="rule-builder-step">
      <p className="rule-builder-prompt">What should this step do?</p>
      <div className="intent-grid">
        {INTENTS.map((item) => (
          <button
            key={item.value}
            type="button"
            className="intent-card"
            onClick={() => dispatch({ type: "SET_INTENT", intent: item.value })}
          >
            <span className="intent-card-label">{item.label}</span>
            <span className="intent-card-hint">{item.hint}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
