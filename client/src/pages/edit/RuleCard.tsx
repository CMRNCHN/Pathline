import type { Step } from "../../script/types";
import { inferIntent, ruleSummary, truncateTrigger } from "../../script/ruleIntent";

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
    <article className="rule-card">
      <div className="rule-card-main">
        <h4 className="rule-card-title">{summary.typeLabel}</h4>

        {intent !== "end" && summary.trigger !== "—" && (
          <div className="rule-card-row">
            <span className="rule-card-key">Trigger</span>
            <span className="rule-card-val">{truncateTrigger(summary.trigger)}</span>
          </div>
        )}

        <div className="rule-card-row">
          <span className="rule-card-key">Action</span>
          <span className="rule-card-val">{summary.action}</span>
        </div>

        {summary.inputVariable && (
          <div className="rule-card-row">
            <span className="rule-card-key">Input</span>
            <span className="rule-card-val mono">{summary.inputVariable}</span>
          </div>
        )}

        {summary.outputVariable && (
          <div className="rule-card-row">
            <span className="rule-card-key">Output</span>
            <span className="rule-card-val mono">{summary.outputVariable}</span>
          </div>
        )}
      </div>

      {!readOnly && (
        <div className="rule-card-actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={onEdit}>
            Edit
          </button>
          <button type="button" className="btn-icon" onClick={onRemove} aria-label="Remove">
            ×
          </button>
        </div>
      )}
    </article>
  );
}
