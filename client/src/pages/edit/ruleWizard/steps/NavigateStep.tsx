import { NAVIGATE_KEYS, NAVIGATE_TRIGGER_PRESETS } from "../../../../script/rulePresets";
import { stepLabel } from "../machine";
import { canProceedFromStep } from "../selectors";
import type { StepProps } from "../types";

export function NavigateStep({ state, dispatch }: StepProps) {
  const { step, navigate, intent } = state;

  if (step === "navigate-mode") {
    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        <div className="intent-grid">
          {(
            [
              { mode: "keypad" as const, label: "Press a key", hint: "Inject DTMF" },
              { mode: "speak" as const, label: "Speak a phrase", hint: "Text response" },
              { mode: "wait" as const, label: "Wait", hint: "Continue listening" },
            ] as const
          ).map((item) => (
            <button
              key={item.mode}
              type="button"
              className={`intent-card${navigate.mode === item.mode ? " selected" : ""}`}
              onClick={() => {
                dispatch({ type: "SET_NAVIGATE_MODE", mode: item.mode });
                dispatch({ type: "NEXT" });
              }}
            >
              <span className="intent-card-label">{item.label}</span>
              <span className="intent-card-hint">{item.hint}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (step === "navigate-action") {
    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        {navigate.mode === "keypad" && (
          <>
            <p className="field-hint">Key</p>
            <div className="key-grid">
              {NAVIGATE_KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={`key-btn${navigate.value === key ? " selected" : ""}`}
                  onClick={() => dispatch({ type: "SET_NAVIGATE_VALUE", value: key })}
                >
                  {key}
                </button>
              ))}
            </div>
          </>
        )}
        {navigate.mode === "speak" && (
          <label className="rule-builder-field">
            <span>Text response</span>
            <input
              className="editor-input"
              value={navigate.value}
              onChange={(e) => dispatch({ type: "SET_NAVIGATE_VALUE", value: e.target.value })}
              placeholder="Yes"
              autoFocus
            />
          </label>
        )}
        {navigate.mode === "wait" && (
          <label className="rule-builder-field">
            <span>How long should the assistant wait?</span>
            <div className="wait-input-row">
              <input
                className="editor-input"
                type="number"
                min={1}
                max={120}
                value={navigate.waitSeconds}
                onChange={(e) =>
                  dispatch({ type: "SET_NAVIGATE_WAIT_SECONDS", waitSeconds: Number(e.target.value) })
                }
                autoFocus
              />
              <span className="wait-suffix">seconds</span>
            </div>
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

  if (step === "navigate-trigger") {
    return (
      <div className="rule-builder-step">
        <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
        <p className="field-hint">Trigger phrase</p>
        <div className="intent-grid intent-grid-single">
          {NAVIGATE_TRIGGER_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              className={`intent-card${navigate.trigger === preset.phrase ? " selected" : ""}`}
              onClick={() => dispatch({ type: "SET_NAVIGATE_TRIGGER", trigger: preset.phrase })}
            >
              <span className="intent-card-label">{preset.label}…</span>
            </button>
          ))}
          <button
            type="button"
            className="intent-card"
            onClick={() => dispatch({ type: "SET_NAVIGATE_TRIGGER", trigger: "" })}
          >
            <span className="intent-card-label">Custom phrase</span>
          </button>
        </div>
        <label className="rule-builder-field">
          <span>Detection phrase</span>
          <input
            className="editor-input"
            value={navigate.trigger}
            onChange={(e) => dispatch({ type: "SET_NAVIGATE_TRIGGER", trigger: e.target.value })}
            placeholder="For billing"
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
