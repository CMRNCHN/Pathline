import type { Step } from "../../script/types";
import { stepDisplay } from "../../script/stepDisplay";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface RuleCardProps {
  rule: Step;
  stepNumber: number;
  readOnly: boolean;
  onEdit: () => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  canMoveUp: boolean;
  canMoveDown: boolean;
}

function Slot({ children, mono = false }: { children: string; mono?: boolean }) {
  return (
    <span
      className={`inline-flex min-h-8 items-center rounded-md border bg-muted/45 px-2.5 py-1 text-sm ${
        mono ? "font-mono" : ""
      }`}
    >
      {children || "—"}
    </span>
  );
}

export function RuleCard({
  rule,
  stepNumber,
  readOnly,
  onEdit,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
}: RuleCardProps) {
  const display = stepDisplay(rule);

  return (
    <Card className="gap-4 p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-baseline gap-3">
          <span className="font-mono text-xs font-bold uppercase tracking-widest text-primary">
            Step {stepNumber}
          </span>
          <span className="truncate text-sm font-medium">{display.label}</span>
        </div>
        {!readOnly && (
          <div className="flex shrink-0 items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={onMoveUp}
              disabled={!canMoveUp}
              aria-label={`Move Step ${stepNumber} up`}
            >
              <ChevronUp />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={onMoveDown}
              disabled={!canMoveDown}
              aria-label={`Move Step ${stepNumber} down`}
            >
              <ChevronDown />
            </Button>
            <Button type="button" variant="secondary" size="sm" onClick={onEdit}>
              Edit
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={onRemove}
              aria-label={`Remove Step ${stepNumber}`}
            >
              <Trash2 />
            </Button>
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2" aria-label={`Step ${stepNumber} instruction`}>
        <strong className="text-xs uppercase tracking-widest text-muted-foreground">When</strong>
        <Slot>{display.cue}</Slot>
        <Slot>{display.match}</Slot>
        <strong className="ml-1 text-xs uppercase tracking-widest text-muted-foreground">Then</strong>
        <Slot>{display.action}</Slot>
        {display.value && <Slot mono>{display.value}</Slot>}
      </div>
    </Card>
  );
}
