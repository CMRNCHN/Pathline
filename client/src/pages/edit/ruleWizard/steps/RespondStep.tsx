import {
  CUSTOM_PRESET_ID,
  findRespondPreset,
  RESPOND_PRESETS,
} from "../../../../script/rulePresets";
import { ruleFieldHint, ruleFieldLabel } from "../../../../script/ruleCopy";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { stepLabel } from "../machine";
import { canProceedFromStep } from "../selectors";
import type { StepProps } from "../types";

export function RespondStep({ state, dispatch }: StepProps) {
  const { step, respond, intent } = state;

  if (step !== "respond-info") return null;
  const preset = findRespondPreset(respond.presetId);
  const variable = respond.variable || preset?.varName || "";

  return (
    <div className="rule-builder-step">
      <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
      <p className="field-hint">Choose the Input, then define when and how Pathline sends it.</p>

      <div className="intent-grid">
        {RESPOND_PRESETS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`intent-card${respond.presetId === item.id ? " selected" : ""}`}
            onClick={() =>
              dispatch({
                type: "SET_RESPOND_PRESET",
                presetId: item.id,
                variable: item.varName,
                trigger: item.triggerHint,
              })
            }
          >
            <span className="intent-card-label">{item.label}</span>
            <span className="intent-card-hint">{item.triggerHint}</span>
          </button>
        ))}
        <button
          type="button"
          className={`intent-card${respond.presetId === CUSTOM_PRESET_ID ? " selected" : ""}`}
          onClick={() =>
            dispatch({
              type: "SET_RESPOND_PRESET",
              presetId: CUSTOM_PRESET_ID,
              variable: "",
              trigger: "",
            })
          }
        >
          <span className="intent-card-label">Custom Input</span>
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="rule-builder-field">
          <span>When · {ruleFieldLabel.cue}</span>
          <Input
            value={respond.trigger}
            onChange={(e) => dispatch({ type: "SET_RESPOND_TRIGGER", trigger: e.target.value })}
            placeholder={preset?.triggerHint ?? "Enter your zip code"}
          />
          <span className="field-hint">{ruleFieldHint.respondTrigger}</span>
        </label>

        <div className="rule-builder-field">
          <span>Then · Send Input</span>
          <div className="radio-row">
            <label className="radio-pill">
              <input
                type="radio"
                name="respond-delivery"
                checked={respond.delivery === "keypad"}
                onChange={() => dispatch({ type: "SET_RESPOND_DELIVERY", delivery: "keypad" })}
              />
              Press keys
            </label>
            <label className="radio-pill">
              <input
                type="radio"
                name="respond-delivery"
                checked={respond.delivery === "speak"}
                onChange={() => dispatch({ type: "SET_RESPOND_DELIVERY", delivery: "speak" })}
              />
              Speak
            </label>
          </div>
          <label className="rule-builder-field">
            <span>{ruleFieldLabel.runValue}</span>
            <Input
              className="font-mono"
              value={variable}
              onChange={(e) =>
                dispatch({
                  type: "SET_RESPOND_VARIABLE",
                  variable: e.target.value.replace(/\s/g, "_"),
                })
              }
              placeholder="zip_code"
            />
            <span className="field-hint">{ruleFieldHint.runValue}</span>
          </label>
        </div>
      </div>

      <div className="rule-builder-actions">
        <Button
          type="button"
          size="sm"
          onClick={() => dispatch({ type: "NEXT" })}
          disabled={!canProceedFromStep(state)}
        >
          Review Step
        </Button>
      </div>
    </div>
  );
}
