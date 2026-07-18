import {
  CAPTURE_PRESETS,
  CUSTOM_PRESET_ID,
  findCapturePreset,
} from "../../../../script/rulePresets";
import { ruleFieldHint, ruleFieldLabel } from "../../../../script/ruleCopy";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { stepLabel } from "../machine";
import { canProceedFromStep } from "../selectors";
import type { StepProps } from "../types";

export function CaptureStep({ state, dispatch }: StepProps) {
  const { step, capture, intent } = state;

  if (step !== "capture-info") return null;
  const preset = findCapturePreset(capture.presetId);

  return (
    <div className="rule-builder-step">
      <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
      <p className="field-hint">Choose a starting point, then adjust the When and Then slots.</p>

      <div className="intent-grid">
        {CAPTURE_PRESETS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`intent-card${capture.presetId === item.id ? " selected" : ""}`}
            onClick={() =>
              dispatch({
                type: "SET_CAPTURE_PRESET",
                presetId: item.id,
                output: item.outputVar,
                trigger: item.triggerHint,
              })
            }
          >
            <span className="intent-card-label">{item.label}</span>
            <span className="intent-card-hint">{item.triggerHint}…</span>
          </button>
        ))}
        <button
          type="button"
          className={`intent-card${capture.presetId === CUSTOM_PRESET_ID ? " selected" : ""}`}
          onClick={() =>
            dispatch({
              type: "SET_CAPTURE_PRESET",
              presetId: CUSTOM_PRESET_ID,
              output: "",
              trigger: "",
            })
          }
        >
          <span className="intent-card-label">Custom</span>
          <span className="intent-card-hint">Define your own phrase and saved value</span>
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="rule-builder-field">
          <span>When · {ruleFieldLabel.cue}</span>
          <Input
            value={capture.trigger}
            onChange={(e) => dispatch({ type: "SET_CAPTURE_TRIGGER", trigger: e.target.value })}
            placeholder={preset?.triggerHint ?? "Your balance is"}
          />
          <span className="field-hint">{ruleFieldHint.captureTrigger}</span>
        </label>

        <div className="rule-builder-field">
          <span>Then</span>
          <div className="radio-row">
            <label className="radio-pill">
              <input
                type="radio"
                name="capture-save"
                checked={capture.save}
                onChange={() => dispatch({ type: "SET_CAPTURE_SAVE", save: true })}
              />
              Save
            </label>
            <label className="radio-pill">
              <input
                type="radio"
                name="capture-save"
                checked={!capture.save}
                onChange={() => dispatch({ type: "SET_CAPTURE_SAVE", save: false })}
              />
              Keep listening
            </label>
          </div>
          {capture.save && (
            <label className="rule-builder-field">
              <span>{ruleFieldLabel.saveAs}</span>
              <Input
                className="font-mono"
                value={capture.output}
                onChange={(e) =>
                  dispatch({
                    type: "SET_CAPTURE_OUTPUT",
                    output: e.target.value.replace(/\s/g, "_"),
                  })
                }
                placeholder="account_balance"
              />
              <span className="field-hint">{ruleFieldHint.saveAs}</span>
            </label>
          )}
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
