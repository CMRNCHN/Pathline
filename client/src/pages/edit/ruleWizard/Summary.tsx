import type { RuleSummary } from "../../../script/ruleIntent";
import { ruleFieldLabel, triggerLabelForIntent } from "../../../script/ruleCopy";
import { summaryEditStep } from "./selectors";
import type { StepProps } from "./types";

interface SummaryProps extends StepProps {
  summary: RuleSummary;
  editing: boolean;
  onSave: () => void;
  onCancel: () => void;
}

function SummaryRow({
  label,
  value,
  editable,
  onEdit,
}: {
  label: string;
  value: string;
  editable?: boolean;
  onEdit?: () => void;
}) {
  return (
    <div className="rule-wizard-summary-row">
      <div className="rule-wizard-summary-row-head">
        <span className="rule-wizard-summary-key">{label}</span>
        {editable && onEdit && (
          <button type="button" className="rule-wizard-summary-edit" onClick={onEdit}>
            Edit
          </button>
        )}
      </div>
      <span className="rule-wizard-summary-val">{value}</span>
    </div>
  );
}

export function Summary({ state, dispatch, summary, editing, onSave, onCancel }: SummaryProps) {
  const goEdit = (field: "trigger" | "action" | "input" | "output") => {
    const step = summaryEditStep(state, field);
    if (step) dispatch({ type: "GO_TO_STEP", step });
  };

  const intent = state.intent;
  const canEditTrigger = intent === "capture" || intent === "navigate" || intent === "respond";
  const canEditAction = intent === "capture" || intent === "navigate" || intent === "respond";
  const canEditInput = intent === "respond";
  const canEditOutput = intent === "capture" && state.capture.save;

  return (
    <div className="rule-builder-step">
      <p className="rule-builder-prompt">Review rule</p>
      <div className="rule-wizard-summary">
        <SummaryRow label="Type" value={summary.typeLabel} />
        {summary.trigger && summary.trigger !== "—" && (
          <SummaryRow
            label={triggerLabelForIntent(intent)}
            value={summary.trigger}
            editable={canEditTrigger}
            onEdit={() => goEdit("trigger")}
          />
        )}
        <SummaryRow
          label={ruleFieldLabel.action}
          value={summary.action}
          editable={canEditAction}
          onEdit={() => goEdit("action")}
        />
        {summary.inputVariable && (
          <SummaryRow
            label={ruleFieldLabel.runValue}
            value={summary.inputVariable}
            editable={canEditInput}
            onEdit={() => goEdit("input")}
          />
        )}
        {summary.outputVariable && (
          <SummaryRow
            label={ruleFieldLabel.saveAs}
            value={summary.outputVariable}
            editable={canEditOutput}
            onEdit={() => goEdit("output")}
          />
        )}
      </div>
      <div className="rule-builder-actions">
        <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="btn btn-primary btn-sm" onClick={onSave}>
          {editing ? "Save rule" : "Save rule"}
        </button>
      </div>
    </div>
  );
}
