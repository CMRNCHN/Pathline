import {
  CUSTOM_PRESET_ID,
  findRespondPreset,
  RESPOND_PRESETS,
} from "../../../../script/rulePresets";
import { stepLabel } from "../machine";
import { canProceedFromStep } from "../selectors";
import type { StepProps } from "../types";

export function RespondStep({ state, dispatch }: StepProps) {
  const { step, respond, intent } = state;

  if (step === "respond-info") {
    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        <div className="intent-grid">
          {RESPOND_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`intent-card${respond.presetId === preset.id ? " selected" : ""}`}
              onClick={() => {
                dispatch({
                  type: "SET_RESPOND_PRESET",
                  presetId: preset.id,
                  variable: preset.varName,
                  trigger: preset.triggerHint,
                });
                dispatch({ type: "NEXT" });
              }}
            >
              <span className="intent-card-label">{preset.label}</span>
              <span className="intent-card-hint">{preset.triggerHint}</span>
            </button>
          ))}
          <button
            type="button"
            className={`intent-card${respond.presetId === CUSTOM_PRESET_ID ? " selected" : ""}`}
            onClick={() => dispatch({ type: "SET_RESPOND_PRESET", presetId: CUSTOM_PRESET_ID })}
          >
            <span className="intent-card-label">Custom value</span>
          </button>
        </div>
        {respond.presetId === CUSTOM_PRESET_ID && (
          <>
            <label className="rule-builder-field">
              <span>Variable name</span>
              <input
                className="editor-input mono"
                value={respond.variable}
                onChange={(e) =>
                  dispatch({
                    type: "SET_RESPOND_VARIABLE",
                    variable: e.target.value.replace(/\s/g, "_"),
                  })
                }
                placeholder="credit_card_number"
                autoFocus
              />
              <span className="field-hint mono">{`{{${respond.variable || "field_name"}}}`}</span>
            </label>
            <div className="rule-builder-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => dispatch({ type: "NEXT" })}
                disabled={!respond.variable.trim()}
              >
                Continue
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  if (step === "respond-delivery") {
    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        <fieldset className="rule-builder-field">
          <div className="radio-row">
            <label className="radio-pill">
              <input
                type="radio"
                name="respond-delivery"
                checked={respond.delivery === "keypad"}
                onChange={() => dispatch({ type: "SET_RESPOND_DELIVERY", delivery: "keypad" })}
              />
              Touchtones (DTMF)
            </label>
            <label className="radio-pill">
              <input
                type="radio"
                name="respond-delivery"
                checked={respond.delivery === "speak"}
                onChange={() => dispatch({ type: "SET_RESPOND_DELIVERY", delivery: "speak" })}
              />
              Speech
            </label>
          </div>
        </fieldset>
        <div className="rule-builder-actions">
          <button type="button" className="btn btn-primary btn-sm" onClick={() => dispatch({ type: "NEXT" })}>
            Continue
          </button>
        </div>
      </div>
    );
  }

  if (step === "respond-variable") {
    const preset = findRespondPreset(respond.presetId);
    const variable = respond.variable || preset?.varName || "";

    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        <label className="rule-builder-field">
          <span>Variable the IVR will receive at run time</span>
          <input
            className="editor-input mono"
            value={variable}
            onChange={(e) =>
              dispatch({
                type: "SET_RESPOND_VARIABLE",
                variable: e.target.value.replace(/\s/g, "_"),
              })
            }
            placeholder="account_number"
            disabled={respond.presetId !== CUSTOM_PRESET_ID && Boolean(preset)}
          />
          <span className="field-hint mono">{`{{${variable || "field_name"}}}`}</span>
          <span className="field-hint">Filled in when you start a run — not stored in the script.</span>
        </label>
        <div className="rule-builder-actions">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => dispatch({ type: "NEXT" })}
            disabled={!variable.trim()}
          >
            Continue
          </button>
        </div>
      </div>
    );
  }

  if (step === "respond-trigger") {
    const preset = findRespondPreset(respond.presetId);
    const hints = preset
      ? [preset.triggerHint]
      : RESPOND_PRESETS.map((p) => p.triggerHint).slice(0, 2);

    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        <p className="field-hint">Trigger phrase</p>
        <div className="intent-grid intent-grid-single">
          {hints.map((phrase) => (
            <button
              key={phrase}
              type="button"
              className={`intent-card${respond.trigger === phrase ? " selected" : ""}`}
              onClick={() => dispatch({ type: "SET_RESPOND_TRIGGER", trigger: phrase })}
            >
              <span className="intent-card-label">{phrase}</span>
            </button>
          ))}
          <button
            type="button"
            className="intent-card"
            onClick={() => dispatch({ type: "SET_RESPOND_TRIGGER", trigger: "" })}
          >
            <span className="intent-card-label">Custom phrase</span>
          </button>
        </div>
        <label className="rule-builder-field">
          <span>Detection phrase</span>
          <input
            className="editor-input"
            value={respond.trigger}
            onChange={(e) => dispatch({ type: "SET_RESPOND_TRIGGER", trigger: e.target.value })}
            placeholder="Please enter your account number"
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

  return null;
}
