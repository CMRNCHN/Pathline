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
  formatOutputDisplay,
  inlineDraftFromStep,
  normalizeKeysValue,
  normalizeOutputName,
  type InlineStepAction,
  type InlineStepDraft,
  validateInlineStepDraft,
} from "../../script/ruleIntent";
import type { Step } from "../../script/types";

const ACTION_OPTIONS: { value: InlineStepAction; label: string }[] = [
  { value: "press-keys", label: "Press keys" },
  { value: "speak", label: "Speak phrase" },
  { value: "save-response", label: "Save response" },
  { value: "keep-listening", label: "Keep listening" },
  { value: "wait", label: "Wait (seconds)" },
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
  onDuplicate?: () => void;
  onMoveUp?: () => void;
  onMoveDown?: () => void;
  onMove?: (fromIndex: number, toIndex: number) => void;
  dragIndex?: number;
  canMoveUp?: boolean;
  canMoveDown?: boolean;
  readOnly?: boolean;
}

function ColLabel({ htmlFor, children }: { htmlFor?: string; children: string }) {
  return (
    <label
      htmlFor={htmlFor}
      className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted-foreground"
    >
      {children}
    </label>
  );
}

function ReadValue({ children, mono }: { children: string; mono?: boolean }) {
  if (!children.trim()) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  return (
    <span
      className={`inline-flex min-h-9 max-w-full items-center rounded-md border border-border bg-background/60 px-2.5 py-1.5 text-sm text-foreground break-words ${
        mono ? "font-mono text-xs" : ""
      }`}
    >
      {children}
    </span>
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

function actionLabel(action: InlineStepAction | ""): string {
  return ACTION_OPTIONS.find((option) => option.value === action)?.label ?? "";
}

function payloadColumnLabel(action: InlineStepAction | ""): string {
  switch (action) {
    case "save-response":
      return "Save to output var";
    case "wait":
      return "Duration (sec)";
    case "press-keys":
    case "speak":
    case "end-call":
      return "Payload";
    case "keep-listening":
      return "Payload";
    default:
      return "Payload";
  }
}

function outputDisplay(draft: InlineStepDraft): string {
  if (draft.action === "press-keys" || draft.action === "speak") return draft.value;
  if (draft.action === "save-response") return formatOutputDisplay(draft.output);
  if (draft.action === "wait") return String(draft.waitSeconds);
  return "";
}

function StepChrome({
  stepNumber,
  action,
  controls,
}: {
  stepNumber: number;
  action: InlineStepAction | "";
  controls?: React.ReactNode;
}) {
  const label = actionLabel(action);
  return (
    <div className="mb-3 flex items-center gap-2.5">
      <span className="step-index-badge" aria-hidden>
        {String(stepNumber).padStart(2, "0")}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="text-sm font-bold tracking-wide uppercase">Step {stepNumber}</span>
          {label ? (
            <span className="text-xs text-muted-foreground">· {label}</span>
          ) : null}
        </div>
      </div>
      {controls}
    </div>
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
  const payloadLabel = payloadColumnLabel(draft.action);
  const payloadHtmlFor =
    draft.action === "save-response" ? outputId : draft.action === "wait" ? waitId : valueId;

  const fields = (
    <div className="grid gap-3 sm:grid-cols-3">
      <div className="space-y-1.5">
        <ColLabel htmlFor={readOnly ? undefined : phraseId}>When heard</ColLabel>
        {readOnly ? (
          <ReadValue>{draft.when || (phraseOptional ? "Any next reply" : "")}</ReadValue>
        ) : (
          <Input
            id={phraseId}
            value={draft.when}
            onChange={(event) => patchDraft({ when: event.target.value })}
            placeholder={phraseOptional ? "Optional phrase" : "IVR phrase"}
            aria-invalid={Boolean(
              validation.errors[0]?.includes("phrase") || validation.errors[0]?.includes("listen")
            )}
          />
        )}
      </div>

      <div className="space-y-1.5">
        <ColLabel htmlFor={readOnly ? undefined : actionId}>Action</ColLabel>
        {readOnly ? (
          <ReadValue>{actionLabel(draft.action)}</ReadValue>
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
        <ColLabel htmlFor={readOnly ? undefined : payloadHtmlFor}>{payloadLabel}</ColLabel>
        {readOnly ? (
          <ReadValue mono={draft.action === "press-keys" || draft.action === "save-response"}>
            {outputDisplay(draft) ||
              (draft.action === "end-call" || draft.action === "keep-listening" ? "—" : "")}
          </ReadValue>
        ) : (
          <>
            {draft.action === "press-keys" && (
              <Input
                id={valueId}
                className="font-mono"
                value={draft.value}
                onChange={(event) => patchDraft({ value: event.target.value })}
                onBlur={() => patchDraft({ value: normalizeKeysValue(draft.value) })}
                placeholder="{{account_number}}"
              />
            )}
            {draft.action === "speak" && (
              <Input
                id={valueId}
                value={draft.value}
                onChange={(event) => patchDraft({ value: event.target.value })}
                placeholder="Yes"
              />
            )}
            {draft.action === "save-response" && (
              <Input
                id={outputId}
                className="font-mono text-primary"
                value={draft.output}
                onChange={(event) =>
                  patchDraft({ output: normalizeOutputName(event.target.value) })
                }
                placeholder="claim_status"
              />
            )}
            {draft.action === "wait" && (
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
            {(draft.action === "keep-listening" ||
              draft.action === "end-call" ||
              !draft.action) && (
              <Input
                id={valueId}
                disabled
                placeholder={draft.action === "end-call" ? "—" : "Value or {{var}}"}
                value=""
              />
            )}
          </>
        )}
      </div>
    </div>
  );

  const controls =
    !readOnly && !isNew ? (
      <div className="flex shrink-0 items-center gap-0.5">
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
          disabled={!onRemove}
          aria-label={`Remove Step ${stepNumber}`}
        >
          <Trash2 />
        </Button>
      </div>
    ) : null;

  return (
    <div
      className={`step-card rounded-xl border px-4 py-3.5 ${
        !validation.valid && isDirty && !readOnly
          ? "border-destructive/40 bg-destructive/5"
          : "border-border bg-card"
      }`}
    >
      <StepChrome stepNumber={stepNumber} action={draft.action} controls={controls} />
      {fields}

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
