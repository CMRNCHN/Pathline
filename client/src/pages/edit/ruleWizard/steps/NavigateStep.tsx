import { DTMF_KEYPAD, sanitizeDtmf } from "../../../../script/rulePresets";
import { ruleFieldHint, ruleFieldLabel } from "../../../../script/ruleCopy";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { stepLabel } from "../machine";
import { canProceedFromStep } from "../selectors";
import type { StepProps } from "../types";

export function NavigateStep({ state, dispatch }: StepProps) {
  const { step, navigate, intent } = state;

  if (step !== "navigate-mode") return null;

  return (
    <div className="rule-builder-step">
      <p className="rule-builder-prompt">{stepLabel(step, intent)}</p>
      <div className="intent-grid">
        {(
          [
            { mode: "keypad" as const, label: "Press keys", hint: "Send digits, #, or *" },
            { mode: "speak" as const, label: "Speak", hint: "Say a short response" },
            { mode: "wait" as const, label: "Wait", hint: "Pause before continuing" },
          ] as const
        ).map((item) => (
          <button
            key={item.mode}
            type="button"
            className={`intent-card${navigate.mode === item.mode ? " selected" : ""}`}
            onClick={() => dispatch({ type: "SET_NAVIGATE_MODE", mode: item.mode })}
          >
            <span className="intent-card-label">{item.label}</span>
            <span className="intent-card-hint">{item.hint}</span>
          </button>
        ))}
      </div>

      {navigate.mode !== "wait" && (
        <label className="rule-builder-field">
          <span>When · {ruleFieldLabel.cue}</span>
          <Input
            value={navigate.trigger}
            onChange={(e) => dispatch({ type: "SET_NAVIGATE_TRIGGER", trigger: e.target.value })}
            placeholder="Enter your zip code"
          />
          <span className="field-hint">{ruleFieldHint.navigateTrigger}</span>
        </label>
      )}

      {navigate.mode === "keypad" && (
        <>
          <label className="rule-builder-field">
            <span>Then · Press keys</span>
            <Input
              className="font-mono"
              value={navigate.value}
              onChange={(e) =>
                dispatch({ type: "SET_NAVIGATE_VALUE", value: sanitizeDtmf(e.target.value) })
              }
              placeholder="20002"
              inputMode="numeric"
            />
            <span className="field-hint">Digits, #, and * are sent in order.</span>
          </label>
          <div className="key-grid key-grid-dtmf">
            {DTMF_KEYPAD.map((key) => (
              <button
                key={key}
                type="button"
                className="key-btn"
                onClick={() =>
                  dispatch({
                    type: "SET_NAVIGATE_VALUE",
                    value: sanitizeDtmf(navigate.value + key),
                  })
                }
              >
                {key}
              </button>
            ))}
          </div>
        </>
      )}

      {navigate.mode === "speak" && (
        <label className="rule-builder-field">
          <span>Then · Speak</span>
          <Input
            value={navigate.value}
            onChange={(e) => dispatch({ type: "SET_NAVIGATE_VALUE", value: e.target.value })}
            placeholder="Yes"
          />
        </label>
      )}

      {navigate.mode === "wait" && (
        <label className="rule-builder-field">
          <span>Then · Wait</span>
          <div className="wait-input-row">
            <Input
              type="number"
              min={1}
              max={120}
              value={navigate.waitSeconds}
              onChange={(e) =>
                dispatch({ type: "SET_NAVIGATE_WAIT_SECONDS", waitSeconds: Number(e.target.value) })
              }
            />
            <span className="wait-suffix">seconds</span>
          </div>
        </label>
      )}

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
