import type { Step } from "../../script/types";
import { inferIntent, ruleSummary, truncateTrigger } from "../../script/ruleIntent";
import { ruleFieldLabel, triggerLabelForIntent } from "../../script/ruleCopy";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface RuleCardProps {
  rule: Step;
  readOnly: boolean;
  onEdit: () => void;
  onRemove: () => void;
}

export function RuleCard({ rule, readOnly, onEdit, onRemove }: RuleCardProps) {
  const summary = ruleSummary(rule);
  const intent = inferIntent(rule);

  return (
    <Card className="flex-row items-start justify-between gap-4">
      <div className="rule-card-main min-w-0 flex-1">
        <h4 className="rule-card-title">{summary.typeLabel}</h4>

        {intent !== "end" && summary.trigger !== "—" && (
          <div className="rule-card-row">
            <span className="rule-card-key">{triggerLabelForIntent(intent)}</span>
            <span className="rule-card-val">{truncateTrigger(summary.trigger)}</span>
          </div>
        )}

        <div className="rule-card-row">
          <span className="rule-card-key">{ruleFieldLabel.action}</span>
          <span className="rule-card-val">{summary.action}</span>
        </div>

        {summary.inputVariable && (
          <div className="rule-card-row">
            <span className="rule-card-key">{ruleFieldLabel.runValue}</span>
            <span className="rule-card-val mono">{summary.inputVariable}</span>
          </div>
        )}

        {summary.outputVariable && (
          <div className="rule-card-row">
            <span className="rule-card-key">{ruleFieldLabel.saveAs}</span>
            <span className="rule-card-val mono">{summary.outputVariable}</span>
          </div>
        )}
      </div>

      {!readOnly && (
        <div className="rule-card-actions">
          <Button type="button" variant="secondary" size="sm" onClick={onEdit}>
            Edit
          </Button>
          <Button type="button" variant="ghost" size="icon-sm" onClick={onRemove} aria-label="Remove">
            ×
          </Button>
        </div>
      )}
    </Card>
  );
}
