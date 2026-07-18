import { useEffect, useReducer } from "react";
import type { Step } from "../../../script/types";
import { Button } from "@/components/ui/button";
import { stepProgress } from "./machine";
import { wizardReducer } from "./reducer";
import { selectCanSave, selectSummary, buildRuleFromState } from "./selectors";
import { initialWizardState, wizardStateFromRule } from "./state";
import { Summary } from "./Summary";
import { CaptureStep } from "./steps/CaptureStep";
import { IntentStep } from "./steps/IntentStep";
import { NavigateStep } from "./steps/NavigateStep";
import { RespondStep } from "./steps/RespondStep";

export interface RuleWizardProps {
  existingLabels: string[];
  editingRule?: Step;
  onSave: (rule: Step) => void;
  onCancel: () => void;
}

export function RuleWizard({ existingLabels, editingRule, onSave, onCancel }: RuleWizardProps) {
  const [state, dispatch] = useReducer(
    wizardReducer,
    editingRule,
    (rule) => initialWizardState(rule)
  );

  useEffect(() => {
    if (editingRule) {
      dispatch({ type: "LOAD_RULE", state: wizardStateFromRule(editingRule, true) });
    }
  }, [editingRule]);

  const summary = selectSummary(state);
  const canSave = selectCanSave(state);
  const progress = stepProgress(state.step, state.intent);

  const handleSave = () => {
    if (!canSave) return;
    const labels = existingLabels.filter((l) => l !== editingRule?.label);
    onSave(buildRuleFromState(state, labels, editingRule?.id, editingRule?.label));
  };

  const { step, intent } = state;
  const isCaptureStep = step.startsWith("capture-");
  const isNavigateStep = step.startsWith("navigate-");
  const isRespondStep = step.startsWith("respond-");

  return (
    <div className="rule-builder rule-wizard">
      <div className="rule-builder-header">
        <h3>{editingRule ? "Edit Step" : "Add Step"}</h3>
        <Button type="button" variant="ghost" size="icon-sm" onClick={onCancel} aria-label="Cancel">
          ×
        </Button>
      </div>

      {step !== "intent" && (
        <Button
          type="button"
          variant="link"
          size="sm"
          className="rule-builder-back h-auto p-0"
          onClick={() => dispatch({ type: "BACK" })}
        >
          ← Back
        </Button>
      )}

      {intent && step !== "intent" && (
        <p className="rule-wizard-step-indicator">
          Step {progress.current} of {progress.total}
        </p>
      )}

      {step === "intent" && <IntentStep state={state} dispatch={dispatch} />}
      {isCaptureStep && <CaptureStep state={state} dispatch={dispatch} />}
      {isNavigateStep && <NavigateStep state={state} dispatch={dispatch} />}
      {isRespondStep && <RespondStep state={state} dispatch={dispatch} />}

      {step === "summary" && summary && (
        <Summary
          state={state}
          dispatch={dispatch}
          summary={summary}
          editing={Boolean(editingRule)}
          onSave={handleSave}
          onCancel={onCancel}
        />
      )}
    </div>
  );
}
