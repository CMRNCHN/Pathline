import type { RuleSummary } from "../../../script/ruleIntent";
import { buildRuleFromDraft } from "../../../script/ruleIntent";
import { stepDisplay } from "../../../script/stepDisplay";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { selectDraft } from "./selectors";
import type { StepProps } from "./types";

interface SummaryProps extends StepProps {
  summary: RuleSummary;
  editing: boolean;
  onSave: () => void;
  onCancel: () => void;
}

function Slot({ children, mono = false }: { children: string; mono?: boolean }) {
  return (
    <span
      className={`inline-flex min-h-9 items-center rounded-md border bg-muted/45 px-3 py-1.5 text-sm ${
        mono ? "font-mono" : ""
      }`}
    >
      {children || "—"}
    </span>
  );
}

export function Summary({ state, dispatch, editing, onSave, onCancel }: SummaryProps) {
  const draft = selectDraft(state);
  if (!draft) return null;
  const preview = stepDisplay(buildRuleFromDraft(draft, []));
  const label = state.label || preview.label;

  return (
    <div className="rule-builder-step">
      <p className="rule-builder-prompt">Review Step</p>
      <div className="rounded-lg border bg-background/55 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <strong className="text-xs uppercase tracking-widest text-muted-foreground">When</strong>
          <Slot>{preview.cue}</Slot>
          <Slot>{preview.match}</Slot>
          <strong className="ml-1 text-xs uppercase tracking-widest text-muted-foreground">Then</strong>
          <Slot>{preview.action}</Slot>
          {preview.value && <Slot mono>{preview.value}</Slot>}
        </div>
      </div>
      <label className="rule-builder-field">
        <span>Label Step</span>
        <Input
          value={label}
          onChange={(event) => dispatch({ type: "SET_LABEL", label: event.target.value })}
          placeholder="Zipcode"
        />
        <span className="field-hint">A short name you will recognize in the Step list and Run log.</span>
      </label>
      <div className="rule-builder-actions">
        <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="button" size="sm" onClick={onSave}>
          {editing ? "Save Step" : "Add Step"}
        </Button>
      </div>
    </div>
  );
}
