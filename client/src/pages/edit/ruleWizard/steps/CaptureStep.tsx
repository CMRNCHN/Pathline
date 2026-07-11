import {
  CAPTURE_PRESETS,
  CUSTOM_PRESET_ID,
  findCapturePreset,
} from "../../../../script/rulePresets";
import { ruleFieldHint, ruleFieldLabel } from "../../../../script/ruleCopy";
import { stepLabel } from "../machine";
import { canProceedFromStep } from "../selectors";
import type { StepProps } from "../types";

export function CaptureStep({ state, dispatch }: StepProps) {
  const { step, capture, intent } = state;

  if (step === "capture-info") {
    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        <div className="intent-grid">
          {CAPTURE_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`intent-card${capture.presetId === preset.id ? " selected" : ""}`}
              onClick={() => {
                dispatch({
                  type: "SET_CAPTURE_PRESET",
                  presetId: preset.id,
                  output: preset.outputVar,
                  trigger: preset.triggerHint,
                });
                dispatch({ type: "NEXT" });
              }}
            >
              <span className="intent-card-label">{preset.label}</span>
              <span className="intent-card-hint">{preset.triggerHint}…</span>
            </button>
          ))}
          <button
            type="button"
            className={`intent-card${capture.presetId === CUSTOM_PRESET_ID ? " selected" : ""}`}
            onClick={() => dispatch({ type: "SET_CAPTURE_PRESET", presetId: CUSTOM_PRESET_ID })}
          >
              <span className="intent-card-label">Custom field</span>
              <span className="intent-card-hint">Name your own saved value</span>
          </button>
        </div>
        {capture.presetId === CUSTOM_PRESET_ID && (
          <>
            <label className="rule-builder-field">
              <span>{ruleFieldLabel.saveAs}</span>
              <input
                className="editor-input mono"
                value={capture.output}
                onChange={(e) =>
                  dispatch({
                    type: "SET_CAPTURE_OUTPUT",
                    output: e.target.value.replace(/\s/g, "_"),
                  })
                }
                placeholder="custom_field"
                autoFocus
              />
            </label>
            <div className="rule-builder-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => dispatch({ type: "NEXT" })}
                disabled={!capture.output.trim()}
              >
                Continue
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  if (step === "capture-trigger") {
    const preset = findCapturePreset(capture.presetId);
    const hints = preset ? [preset.triggerHint] : ["Your claim status is", "Your balance is"];

    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
          <p className="field-hint">{ruleFieldHint.captureTrigger}</p>
        <div className="intent-grid intent-grid-single">
          {hints.map((phrase) => (
            <button
              key={phrase}
              type="button"
              className={`intent-card${capture.trigger === phrase ? " selected" : ""}`}
              onClick={() => dispatch({ type: "SET_CAPTURE_TRIGGER", trigger: phrase })}
            >
              <span className="intent-card-label">{phrase}…</span>
            </button>
          ))}
          <button
            type="button"
            className="intent-card"
            onClick={() => dispatch({ type: "SET_CAPTURE_TRIGGER", trigger: "" })}
          >
            <span className="intent-card-label">Custom phrase</span>
          </button>
        </div>
          <label className="rule-builder-field">
            <span>{ruleFieldLabel.whenIvrSays}</span>
            <input
            className="editor-input"
            value={capture.trigger}
            onChange={(e) => dispatch({ type: "SET_CAPTURE_TRIGGER", trigger: e.target.value })}
            placeholder="Your claim status is"
            autoFocus
          />
        </label>
        <div className="rule-builder-actions">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => dispatch({ type: "NEXT" })}
            disabled={!canProceedFromStep(state)}
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  if (step === "capture-save") {
    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        <fieldset className="rule-builder-field">
          <div className="radio-row">
            <label className="radio-pill">
              <input
                type="radio"
                name="capture-save"
                checked={capture.save}
                onChange={() => dispatch({ type: "SET_CAPTURE_SAVE", save: true })}
              />
              Yes — save what you hear
            </label>
              <label className="radio-pill">
                <input
                  type="radio"
                  name="capture-save"
                  checked={!capture.save}
                  onChange={() => dispatch({ type: "SET_CAPTURE_SAVE", save: false })}
                />
                No — keep listening
              </label>
          </div>
        </fieldset>
        {capture.save && (
            <label className="rule-builder-field">
              <span>{ruleFieldLabel.saveAs}</span>
              <input
                className="editor-input mono"
                value={capture.output}
                onChange={(e) =>
                  dispatch({
                    type: "SET_CAPTURE_OUTPUT",
                    output: e.target.value.replace(/\s/g, "_"),
                  })
                }
                placeholder="claim_status"
              />
              <span className="field-hint">{ruleFieldHint.saveAs}</span>
              <span className="field-hint mono">{`{{${capture.output || "field_name"}}}`}</span>
            </label>
        )}
        <div className="rule-builder-actions">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => dispatch({ type: "NEXT" })}
            disabled={!canProceedFromStep(state)}
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  return null;
}
