import type { RuleWizardType } from "../../../../script/ruleIntent";
import type { StepProps } from "../types";

const INTENTS: { value: RuleWizardType; label: string; hint: string }[] = [
  { value: "capture", label: "Collect information from the IVR", hint: "Save something the IVR says aloud" },
  { value: "navigate", label: "Navigate through the IVR", hint: "Press keys, speak, or wait for menus" },
  { value: "respond", label: "Provide information to the IVR", hint: "Send account details when asked" },
  { value: "end", label: "End the call", hint: "Finish when this step runs" },
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
