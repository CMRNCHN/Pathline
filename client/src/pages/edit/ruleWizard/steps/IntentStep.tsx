import type { RuleWizardType } from "../../../../script/ruleIntent";
import type { StepProps } from "../types";

const INTENTS: { value: RuleWizardType; label: string; hint: string }[] = [
  {
    value: "capture",
    label: "Save what the IVR says",
    hint: "When a phrase matches → save the response",
  },
  {
    value: "navigate",
    label: "Press keys, speak, or wait",
    hint: "When a phrase matches → take one action",
  },
  {
    value: "respond",
    label: "Send an Input",
    hint: "When the IVR asks → send a Run value",
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
