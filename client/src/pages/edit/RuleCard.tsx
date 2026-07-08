import type { IvrRule } from "../../script/types";
import {
  inferIntent,
  ruleCardAction,
  ruleCardTitle,
  truncateTrigger,
} from "../../script/ruleIntent";

interface RuleCardProps {
  rule: IvrRule;
  readOnly: boolean;
  onEdit: () => void;
  onRemove: () => void;
}

export function RuleCard({ rule, readOnly, onEdit, onRemove }: RuleCardProps) {
  const intent = inferIntent(rule);
  const varMatch = rule.response.match(/\{\{(\w+)\}\}/);

  return (
    <article className="rule-card">
      <div className="rule-card-main">
        <h4 className="rule-card-title">{ruleCardTitle(rule)}</h4>

        {intent === "navigate" && (
          <>
            <div className="rule-card-row">
              <span className="rule-card-key">When hearing</span>
              <span className="rule-card-val">{truncateTrigger(rule.trigger)}</span>
            </div>
            <div className="rule-card-row">
              <span className="rule-card-key">Action</span>
              <span className="rule-card-val">{ruleCardAction(rule)}</span>
            </div>
            <div className="rule-card-row">
              <span className="rule-card-key">Value</span>
              <span className="rule-card-val mono">{varMatch?.[1] ?? "—"}</span>
            </div>
          </>
        )}

        {intent === "capture" && (
          <>
            <div className="rule-card-row">
              <span className="rule-card-key">When hearing</span>
              <span className="rule-card-val">{truncateTrigger(rule.trigger)}</span>
            </div>
            <div className="rule-card-row">
              <span className="rule-card-key">Action</span>
              <span className="rule-card-val">{ruleCardAction(rule)}</span>
            </div>
            <div className="rule-card-row">
              <span className="rule-card-key">Result</span>
              <span className="rule-card-val mono">{rule.output}</span>
            </div>
          </>
        )}

        {intent === "wait" && (
          <div className="rule-card-row">
            <span className="rule-card-key">Action</span>
            <span className="rule-card-val">Wait {rule.waitSeconds ?? 3} seconds</span>
          </div>
        )}

        {intent === "end" && (
          <div className="rule-card-row">
            <span className="rule-card-key">Action</span>
            <span className="rule-card-val">{ruleCardAction(rule)}</span>
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
