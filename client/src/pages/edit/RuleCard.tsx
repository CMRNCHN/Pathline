import type { Step } from "../../script/types";
import { inlineDraftFromStep } from "../../script/ruleIntent";
import { InlineStepRow } from "./InlineStepRow";

interface RuleCardProps {
  rule: Step;
  stepNumber: number;
}

/** Read-only step — same structured layout as the editor. */
export function RuleCard({ rule, stepNumber }: RuleCardProps) {
  const draft = inlineDraftFromStep(rule);
  return (
    <InlineStepRow
      step={rule}
      stepNumber={stepNumber}
      existingLabels={[rule.label]}
      onSave={() => {}}
      readOnly
      // Draft fields are driven from `step`; keep labels stable for aria.
      key={`${rule.id}-${draft.action}`}
    />
  );
}
