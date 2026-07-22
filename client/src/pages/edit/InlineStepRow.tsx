import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
const AUTO_SAVE_MS = 350;

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
  readOnly?: boolean;
}

function FieldLabel({
  htmlFor,
  children,
  optional,
}: {
  htmlFor: string;
  children: string;
  optional?: boolean;
}) {
  return (
    <label htmlFor={htmlFor} className="text-xs font-medium text-muted-foreground">
      {children}
      {optional ? <span className="font-normal"> (optional)</span> : null}
    </label>
  );
}

function draftsEqual(a: InlineStepDraft, b: InlineStepDraft): boolean {
  return (
    a.when === b.when &&
    a.action === b.action &&
    a.value === b.value &&
    a.output === b.output &&
    a.waitSeconds === b.waitSeconds
  );
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
  readOnly = false,
}: InlineStepRowProps) {
  const initialDraft = () => (step ? inlineDraftFromStep(step) : emptyInlineStepDraft());
  const [draft, setDraft] = useState<InlineStepDraft>(initialDraft);
  const validation = validateInlineStepDraft(draft);
  const isNew = !step;
  const waitOptions = WAIT_OPTIONS.includes(draft.waitSeconds)
    ? WAIT_OPTIONS
    : [...WAIT_OPTIONS, draft.waitSeconds].sort((a, b) => a - b);
  const phraseOptional =
    draft.action === "save-response" || draft.action === "end-call" || draft.action === "wait";
  const savedSnapshot = step ? inlineDraftFromStep(step) : null;
  const isDirty = !savedSnapshot || !draftsEqual(draft, savedSnapshot);
  const skipNextSync = useRef(false);
  const onSaveRef = useRef(onSave);
  const labelsRef = useRef(existingLabels);
  onSaveRef.current = onSave;
  labelsRef.current = existingLabels;

  useEffect(() => {
    if (!step) return;
    if (skipNextSync.current) {
      skipNextSync.current = false;
      return;
    }
    setDraft(inlineDraftFromStep(step));
  }, [step]);

  useEffect(() => {
    if (readOnly || !validation.valid || !draft.action) return;
    if (!isNew && !isDirty) return;

    const timer = window.setTimeout(() => {
      try {
        const next = buildStepFromInlineDraft(draft, labelsRef.current, step);
        skipNextSync.current = true;
        onSaveRef.current(next);
      } catch {
        // Validation already gates; ignore race with incomplete draft.
      }
    }, AUTO_SAVE_MS);

    return () => window.clearTimeout(timer);
  }, [draft, validation.valid, isDirty, isNew, step, readOnly]);

  const patchDraft = (patch: Partial<InlineStepDraft>) =>
    setDraft((current) => ({ ...current, ...patch }));

  const handleActionChange = (action: InlineStepAction) => {
    patchDraft({
      action,
      value: action === "press-keys" || action === "speak" ? draft.value : "",
      output: action === "save-response" ? draft.output : "",
      waitSeconds: action === "wait" ? draft.waitSeconds || 3 : 3,
    });
  };

  const phraseId = `step-${stepNumber}-phrase`;
  const actionId = `step-${stepNumber}-action`;
  const valueId = `step-${stepNumber}-value`;
  const outputId = `step-${stepNumber}-output`;
  const waitId = `step-${stepNumber}-wait`;

  return (
    <div
      className={`rounded-lg border px-4 py-3 ${
        !validation.valid && isDirty
          ? "border-destructive/40 bg-destructive/5"
          : "border-border bg-card/40"
      }`}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="font-mono text-xs font-bold uppercase tracking-widest text-primary">
          Step {stepNumber}
        </span>
        {!readOnly && !isNew && (
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

      <div className="grid gap-3 sm:grid-cols-[minmax(0,1.4fr)_minmax(10rem,0.9fr)_minmax(0,1fr)]">
        <div className="space-y-1.5">
          <FieldLabel htmlFor={phraseId} optional={phraseOptional}>
            Listen for
          </FieldLabel>
          <Input
            id={phraseId}
            value={draft.when}
            onChange={(event) => patchDraft({ when: event.target.value })}
            placeholder={
              draft.action === "save-response"
                ? "Leave blank for next reply"
                : draft.action === "end-call"
                  ? "Leave blank to hang up after prior Steps"
                  : draft.action === "wait"
                    ? "Optional cue phrase"
                    : "IVR phrase"
            }
            disabled={readOnly}
            aria-invalid={Boolean(
              validation.errors[0]?.includes("phrase") || validation.errors[0]?.includes("listen")
            )}
          />
          {phraseOptional && !readOnly && (
            <p className="text-xs text-muted-foreground">
              {draft.action === "save-response"
                ? "Blank saves the next reply after earlier Steps finish."
                : draft.action === "end-call"
                  ? "Blank hangs up after earlier Steps finish."
                  : "Optional cue while waiting."}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <FieldLabel htmlFor={actionId}>Then</FieldLabel>
          {readOnly ? (
            <Input
              id={actionId}
              value={ACTION_OPTIONS.find((option) => option.value === draft.action)?.label ?? draft.action}
              disabled
            />
          ) : (
            <Select
              value={draft.action || undefined}
              onValueChange={(value) => {
                if (value) handleActionChange(value as InlineStepAction);
              }}
            >
              <SelectTrigger id={actionId} className="w-full" aria-invalid={!draft.action}>
                <SelectValue placeholder="Choose action" />
              </SelectTrigger>
              <SelectContent>
                {ACTION_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        <div className="space-y-1.5">
          {(draft.action === "press-keys" || draft.action === "speak") && (
            <>
              <FieldLabel htmlFor={valueId}>
                {draft.action === "press-keys" ? "Keys" : "Say"}
              </FieldLabel>
              <Input
                id={valueId}
                className={draft.action === "press-keys" ? "font-mono" : undefined}
                value={draft.value}
                onChange={(event) => patchDraft({ value: event.target.value })}
                placeholder={draft.action === "press-keys" ? "1 or {{account_pin}}#" : "Yes"}
                disabled={readOnly}
              />
            </>
          )}

          {draft.action === "save-response" && (
            <>
              <FieldLabel htmlFor={outputId}>Save as</FieldLabel>
              <Input
                id={outputId}
                className="font-mono"
                value={draft.output}
                onChange={(event) => patchDraft({ output: event.target.value.replace(/\s+/g, "_") })}
                placeholder="card_status"
                disabled={readOnly}
              />
            </>
          )}

          {draft.action === "wait" && (
            <>
              <FieldLabel htmlFor={waitId}>Seconds</FieldLabel>
              {readOnly ? (
                <Input id={waitId} value={String(draft.waitSeconds)} disabled />
              ) : (
                <Select
                  value={String(draft.waitSeconds)}
                  onValueChange={(value) => {
                    if (value) patchDraft({ waitSeconds: Number(value) });
                  }}
                >
                  <SelectTrigger id={waitId} className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {waitOptions.map((seconds) => (
                      <SelectItem key={seconds} value={String(seconds)}>
                        {seconds}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </>
          )}

          {(draft.action === "keep-listening" || draft.action === "end-call" || !draft.action) && (
            <p className="pt-6 text-xs text-muted-foreground">
              {draft.action === "end-call"
                ? "No value needed."
                : draft.action === "keep-listening"
                  ? "Continues listening for this phrase."
                  : "Choose an action."}
            </p>
          )}
        </div>
      </div>

      {!readOnly && validation.errors.length > 0 && isDirty && (
        <p className="mt-3 text-sm text-destructive" role="alert">
          {validation.errors[0]}
        </p>
      )}

      {!readOnly && isNew && (
        <div className="mt-3 flex justify-end">
          <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}
