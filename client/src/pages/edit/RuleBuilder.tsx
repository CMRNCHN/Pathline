import { useMemo, useState } from "react";
import type { IvrRule } from "../../script/types";
import {
  buildRuleFromDraft,
  type NavigateMode,
  type RuleDraft,
  type RuleIntent,
  ruleToDraft,
} from "../../script/ruleIntent";

const INTENTS: { value: RuleIntent; label: string; hint: string }[] = [
  { value: "navigate", label: "Navigate the IVR", hint: "Send DTMF when the IVR asks for input" },
  { value: "capture", label: "Capture information", hint: "Save something the IVR says aloud" },
  { value: "wait", label: "Wait", hint: "Pause before the next step" },
  { value: "end", label: "End the call", hint: "Finish when this step runs" },
];

interface RuleBuilderProps {
  runtimeVariables: string[];
  existingLabels: string[];
  editingRule?: IvrRule;
  onAddVariable: (name: string) => void;
  onSave: (rule: IvrRule) => void;
  onCancel: () => void;
}

export function RuleBuilder({
  runtimeVariables,
  existingLabels,
  editingRule,
  onAddVariable,
  onSave,
  onCancel,
}: RuleBuilderProps) {
  const initial = useMemo(
    () => (editingRule ? ruleToDraft(editingRule) : null),
    [editingRule]
  );

  const [intent, setIntent] = useState<RuleIntent | null>(initial?.intent ?? null);
  const [trigger, setTrigger] = useState(
    initial && "trigger" in initial ? initial.trigger : ""
  );
  const [mode] = useState<NavigateMode>("keypad");
  const [variable, setVariable] = useState(
    initial?.intent === "navigate" ? initial.variable : runtimeVariables[0] ?? ""
  );
  const [newVariable, setNewVariable] = useState("");
  const [output, setOutput] = useState(
    initial?.intent === "capture" ? initial.output : ""
  );
  const [waitSeconds, setWaitSeconds] = useState(
    initial?.intent === "wait" ? initial.waitSeconds : 3
  );

  const draft = useMemo((): RuleDraft | null => {
    if (!intent) return null;
    switch (intent) {
      case "navigate":
        if (!trigger.trim() || !variable.trim()) return null;
        return { intent, trigger, mode, variable: variable.trim() };
      case "capture":
        if (!trigger.trim() || !output.trim()) return null;
        return { intent, trigger, output: output.trim() };
      case "wait":
        if (waitSeconds < 1) return null;
        return { intent, waitSeconds };
      case "end":
        return { intent };
    }
  }, [intent, trigger, mode, variable, output, waitSeconds]);

  const canSave = draft !== null;

  const handleSave = () => {
    if (!draft) return;
    const labels = existingLabels.filter((l) => l !== editingRule?.label);
    onSave(
      buildRuleFromDraft(draft, labels, editingRule?.id, editingRule?.label)
    );
  };

  const handleAddVariable = () => {
    const name = newVariable.replace(/\s/g, "_").trim();
    if (!name) return;
    onAddVariable(name);
    setVariable(name);
    setNewVariable("");
  };

  return (
    <div className="rule-builder">
      <div className="rule-builder-header">
        <h3>{editingRule ? "Edit step" : "Add a step"}</h3>
        <button type="button" className="btn-icon" onClick={onCancel} aria-label="Cancel">
          ×
        </button>
      </div>

      {!intent ? (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">What would you like to do?</p>
          <div className="intent-grid">
            {INTENTS.map((item) => (
              <button
                key={item.value}
                type="button"
                className="intent-card"
                onClick={() => setIntent(item.value)}
              >
                <span className="intent-card-label">{item.label}</span>
                <span className="intent-card-hint">{item.hint}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <>
          <button type="button" className="rule-builder-back" onClick={() => setIntent(null)}>
            ← Change action
          </button>

          {intent === "navigate" && (
            <div className="rule-builder-step">
              <label className="rule-builder-field">
                <span>What should the assistant listen for?</span>
                <input
                  className="editor-input"
                  value={trigger}
                  onChange={(e) => setTrigger(e.target.value)}
                  placeholder="Please enter your account number"
                  autoFocus
                />
              </label>

              <fieldset className="rule-builder-field">
                <legend>Response</legend>
                <p className="field-hint">Press keypad buttons on your phone when this phrase is matched.</p>
              </fieldset>

              <label className="rule-builder-field">
                <span>Which value should it use?</span>
                {runtimeVariables.length > 0 ? (
                  <select
                    className="editor-input mono"
                    value={variable}
                    onChange={(e) => setVariable(e.target.value)}
                  >
                    {runtimeVariables.map((v) => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                ) : (
                  <p className="field-hint warn">Add a run value in Setup first.</p>
                )}
              </label>

              <div className="rule-builder-inline-add">
                <input
                  className="editor-input mono"
                  value={newVariable}
                  onChange={(e) => setNewVariable(e.target.value.replace(/\s/g, "_"))}
                  placeholder="new_value_name"
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleAddVariable}
                  disabled={!newVariable.trim()}
                >
                  Add value
                </button>
              </div>
            </div>
          )}

          {intent === "capture" && (
            <div className="rule-builder-step">
              <label className="rule-builder-field">
                <span>What should the assistant listen for?</span>
                <input
                  className="editor-input"
                  value={trigger}
                  onChange={(e) => setTrigger(e.target.value)}
                  placeholder="Your current balance is"
                  autoFocus
                />
              </label>
              <label className="rule-builder-field">
                <span>What information should be saved?</span>
                <input
                  className="editor-input mono"
                  value={output}
                  onChange={(e) => setOutput(e.target.value.replace(/\s/g, "_"))}
                  placeholder="account_balance"
                />
              </label>
            </div>
          )}

          {intent === "wait" && (
            <div className="rule-builder-step">
              <label className="rule-builder-field">
                <span>How long should the assistant wait?</span>
                <div className="wait-input-row">
                  <input
                    className="editor-input"
                    type="number"
                    min={1}
                    max={120}
                    value={waitSeconds}
                    onChange={(e) => setWaitSeconds(Number(e.target.value))}
                    autoFocus
                  />
                  <span className="wait-suffix">seconds</span>
                </div>
              </label>
            </div>
          )}

          {intent === "end" && (
            <p className="field-hint">This step ends the run when reached.</p>
          )}

          <div className="rule-builder-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleSave}
              disabled={!canSave}
            >
              {editingRule ? "Save changes" : "Add step"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
