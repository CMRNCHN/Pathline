import type { RuleSummary } from "../../../script/ruleIntent";
import { ruleFieldLabel, triggerLabelForIntent } from "../../../script/ruleCopy";
import { Button } from "@/components/ui/button";
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
          <Button
            type="button"
            variant="link"
            size="sm"
            className="rule-wizard-summary-edit h-auto p-0"
            onClick={onEdit}
          >
            Edit
          </Button>
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
        <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="button" size="sm" onClick={onSave}>
          {editing ? "Save rule" : "Save rule"}
        </Button>
      </div>
    </div>
  );
}
