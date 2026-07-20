import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  buildStepFromInlineDraft,
  emptyInlineStepDraft,
  inlineDraftFromStep,
  type InlineStepAction,
  type InlineStepDraft,
  validateInlineStepDraft,
} from "../../script/ruleIntent";
import type { Step } from "../../script/types";

const ACTION_OPTIONS: { value: InlineStepAction; label: string }[] = [
  { value: "press-keys", label: "Press keys" },
  { value: "speak", label: "Speak" },
  { value: "save-response", label: "Save response" },
  { value: "keep-listening", label: "Keep listening" },
  { value: "wait", label: "Wait" },
  { value: "end-call", label: "End call" },
];

const WAIT_OPTIONS = [1, 3, 5, 10, 15, 30, 60, 120];
const SELECT_CLASS =
  "h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

interface InlineStepRowProps {
  step?: Step;
  stepNumber: number;
  existingLabels: string[];
  onSave: (step: Step) => void;
  onCancel?: () => void;
  onRemove?: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  canMoveUp?: boolean;
  canMoveDown?: boolean;
}

export function InlineStepRow({
  step,
  stepNumber,
  existingLabels,
  onSave,
  onCancel,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp = false,
  canMoveDown = false,
}: InlineStepRowProps) {
  const initialDraft = () => (step ? inlineDraftFromStep(step) : emptyInlineStepDraft());
  const [draft, setDraft] = useState<InlineStepDraft>(initialDraft);
  const validation = validateInlineStepDraft(draft);
  const isNew = !step;
  const waitOptions = WAIT_OPTIONS.includes(draft.waitSeconds)
    ? WAIT_OPTIONS
    : [...WAIT_OPTIONS, draft.waitSeconds].sort((a, b) => a - b);

  useEffect(() => {
    if (step) setDraft(inlineDraftFromStep(step));
  }, [step]);

  const patchDraft = (patch: Partial<InlineStepDraft>) =>
    setDraft((current) => ({ ...current, ...patch }));

  const handleActionChange = (action: InlineStepDraft["action"]) => {
    patchDraft({
      action,
      value: action === "press-keys" || action === "speak" ? draft.value : "",
      output: action === "save-response" ? draft.output : "",
      waitSeconds: action === "wait" ? draft.waitSeconds || 3 : 3,
    });
  };

  const handleSave = () => {
    if (!validation.valid) return;
    onSave(buildStepFromInlineDraft(draft, existingLabels, step));
  };

  const handleReset = () => {
    if (isNew) {
      onCancel?.();
      return;
    }
    setDraft(initialDraft());
  };

  return (
    <Card className="gap-3 p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-xs font-bold uppercase tracking-widest text-primary">
          Step {stepNumber}
        </span>
        {!isNew && (
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

      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium">When</span>
        <Input
          className="min-w-52 flex-1"
          value={draft.when}
          onChange={(event) => patchDraft({ when: event.target.value })}
          placeholder={
            draft.action === "wait"
              ? "custom phrase (optional)"
              : draft.action === "end-call"
                ? "cue phrase (optional — blank = hang up after prior Steps)"
                : draft.action === "save-response"
                  ? "cue phrase (optional — blank = next reply)"
                  : "custom phrase"
          }
          aria-label={`Step ${stepNumber} phrase`}
        />
        <span className="font-medium">is heard,</span>
        <select
          className={SELECT_CLASS}
          value={draft.action}
          onChange={(event) => handleActionChange(event.target.value as InlineStepDraft["action"])}
          aria-label={`Step ${stepNumber} action`}
          aria-invalid={!draft.action}
        >
          {!draft.action && <option value="">Unsupported existing action</option>}
          {ACTION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        {(draft.action === "press-keys" || draft.action === "speak") && (
          <Input
            className={draft.action === "press-keys" ? "min-w-40 flex-1 font-mono" : "min-w-40 flex-1"}
            value={draft.value}
            onChange={(event) => patchDraft({ value: event.target.value })}
            placeholder={draft.action === "press-keys" ? "1 or {{account_pin}}#" : "Yes"}
            aria-label={`Step ${stepNumber} ${draft.action === "press-keys" ? "keys" : "speech"}`}
          />
        )}

        {draft.action === "save-response" && (
          <Input
            className="min-w-40 flex-1 font-mono"
            value={draft.output}
            onChange={(event) => patchDraft({ output: event.target.value.replace(/\s+/g, "_") })}
            placeholder="response_name"
            aria-label={`Step ${stepNumber} output name`}
          />
        )}

        {draft.action === "wait" && (
          <>
            <select
              className={SELECT_CLASS}
              value={draft.waitSeconds}
              onChange={(event) => patchDraft({ waitSeconds: Number(event.target.value) })}
              aria-label={`Step ${stepNumber} wait duration`}
            >
              {waitOptions.map((seconds) => (
                <option key={seconds} value={seconds}>
                  {seconds}
                </option>
              ))}
            </select>
            <span>seconds</span>
          </>
        )}
        <span aria-hidden="true">.</span>
      </div>

      {validation.errors.length > 0 && (
        <p className="text-sm text-destructive" role="alert">
          {validation.errors[0]}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={handleReset}>
          {isNew ? "Cancel" : "Reset"}
        </Button>
        <Button type="button" size="sm" onClick={handleSave} disabled={!validation.valid}>
          Save Step
        </Button>
      </div>
    </Card>
  );
}
