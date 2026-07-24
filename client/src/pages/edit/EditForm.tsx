import { useEffect, useMemo, useState } from "react";
import { Copy, Pencil, Play, Save, Trash2 } from "lucide-react";
import type { Step, PathDocument } from "../../script/types";
import { extractOutputRules, extractVariableNames, withSyncedRules } from "../../script/compile";
import { scriptDisplayName } from "../../script/storage";
import { getPathReadiness, getWorkflowSetupIssues, READINESS_LABEL } from "../../script/pathReadiness";
import { loadRunSecretsDraft, saveRunSecretsDraft } from "../../script/runSecretsDraft";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { InlineStepRow } from "./InlineStepRow";
import {
  buildStepFromInlineDraft,
  formatOutputDisplay,
  inlineDraftFromStep,
  isPlaceholderRule,
} from "../../script/ruleIntent";

export interface EditFormProps {
  script: PathDocument;
  readOnly: boolean;
  onPatch: (patch: Partial<PathDocument>) => void;
  onDuplicate: () => void;
  onExport?: () => void;
  onDelete?: () => void;
  onTest?: () => void;
}

function readinessBadgeVariant(readiness: ReturnType<typeof getPathReadiness>) {
  if (readiness === "ready") return "default" as const;
  if (readiness === "needs-setup") return "secondary" as const;
  return "outline" as const;
}

function fieldErrorClass(invalid: boolean) {
  return invalid ? "border-destructive aria-invalid:border-destructive" : undefined;
}

function splitPhrases(when: string): string[] {
  return when
    .split("|")
    .map((part) => part.trim())
    .filter(Boolean);
}

export function EditForm({
  script,
  readOnly,
  onPatch,
  onDuplicate,
  onExport,
  onDelete,
  onTest,
}: EditFormProps) {
  const [addingStep, setAddingStep] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);
  const [secrets, setSecrets] = useState<Record<string, string>>(() =>
    loadRunSecretsDraft(script.id)
  );

  useEffect(() => {
    setSecrets(loadRunSecretsDraft(script.id));
  }, [script.id]);

  const patchSetup = (patch: Partial<PathDocument["setup"]>) =>
    onPatch({ setup: { ...script.setup, ...patch } });

  const inputVariables = extractVariableNames(script);
  const visibleRules = script.steps.filter((r) => !isPlaceholderRule(r));
  const stepLabels = visibleRules.map((item) => item.label);
  const readiness = getPathReadiness(script);
  const setupIssues = getWorkflowSetupIssues(script);
  const runRules = useMemo(() => extractOutputRules(script), [script]);

  const phoneMissing = !script.setup.target.trim();
  const needsSteps = setupIssues.some((issue) => issue.includes("at least one Step"));
  const needsEndCall = setupIssues.some((issue) => issue.includes("End call"));
  const inputSyncIssues = setupIssues.filter((issue) => issue.startsWith("Synchronize"));

  const updateRules = (steps: Step[]) => onPatch(withSyncedRules(script, steps));

  const handleSaveStep = (step: Step) => {
    const existing = visibleRules.some((item) => item.id === step.id);
    updateRules(
      existing
        ? visibleRules.map((item) => (item.id === step.id ? step : item))
        : [...visibleRules, step]
    );
    setAddingStep(false);
  };

  const moveStep = (from: number, to: number) => {
    if (to < 0 || to >= visibleRules.length) return;
    const reordered = [...visibleRules];
    const [step] = reordered.splice(from, 1);
    reordered.splice(to, 0, step);
    updateRules(reordered);
  };

  const removeStep = (step: Step, stepNumber: number) => {
    if (!window.confirm(`Remove Step ${stepNumber} (${step.label})?`)) return;
    updateRules(visibleRules.filter((item) => item.id !== step.id));
  };

  const duplicateStep = (step: Step, index: number) => {
    const draft = inlineDraftFromStep(step);
    try {
      const clone = buildStepFromInlineDraft(draft, stepLabels);
      const next = [...visibleRules];
      next.splice(index + 1, 0, clone);
      updateRules(next);
    } catch {
      // Invalid source step — ignore.
    }
  };

  const patchSecret = (name: string, value: string) => {
    setSecrets((current) => {
      const next = { ...current, [name]: value };
      saveRunSecretsDraft(script.id, next);
      return next;
    });
  };

  const updateRunRulePhrases = (stepId: string, phrases: string[]) => {
    updateRules(
      visibleRules.map((step) =>
        step.id === stepId ? { ...step, when: phrases.join("|") } : step
      )
    );
  };

  const handleEdit = () => {
    if (readOnly) {
      onDuplicate();
      return;
    }
    const input = document.getElementById("workflow-title") as HTMLInputElement | null;
    input?.focus();
    input?.select();
  };

  const handleSaveExisting = () => {
    onExport?.();
    setSavedFlash(true);
    window.setTimeout(() => setSavedFlash(false), 1200);
  };

  return (
    <TooltipProvider>
      <div className="script-editor-panel editor-compact">
        <header className="editor-topbar editor-identity-card">
          <div className="editor-identity-row">
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <Badge variant={readinessBadgeVariant(readiness)} className="shrink-0">
                  {READINESS_LABEL[readiness]}
                </Badge>
              </div>
              {readOnly ? (
                <h1 className="editor-title">{scriptDisplayName(script)}</h1>
              ) : (
                <Input
                  id="workflow-title"
                  className="script-header-name"
                  value={script.setup.name}
                  onChange={(e) => patchSetup({ name: e.target.value })}
                  placeholder="Untitled Workflow"
                  aria-label="Workflow name"
                />
              )}
            </div>

            <div className="editor-identity-actions">
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={handleEdit}
                      aria-label={readOnly ? "Duplicate to edit" : "Edit title"}
                    >
                      <Pencil />
                    </Button>
                  }
                />
                <TooltipContent>{readOnly ? "Duplicate to edit" : "Edit title"}</TooltipContent>
              </Tooltip>
              {!readOnly && onExport && (
                <Tooltip>
                  <TooltipTrigger
                    render={
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={handleSaveExisting}
                        aria-label="Save existing template"
                      >
                        <Save />
                      </Button>
                    }
                  />
                  <TooltipContent>
                    {savedFlash ? "Saved" : "Save existing template"}
                  </TooltipContent>
                </Tooltip>
              )}
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={onDuplicate}
                      aria-label="Save as new template"
                    >
                      <Copy />
                    </Button>
                  }
                />
                <TooltipContent>Save as new template</TooltipContent>
              </Tooltip>
              {onDelete && (
                <Tooltip>
                  <TooltipTrigger
                    render={
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={onDelete}
                        aria-label="Delete Workflow"
                      >
                        <Trash2 />
                      </Button>
                    }
                  />
                  <TooltipContent>Delete</TooltipContent>
                </Tooltip>
              )}
            </div>
          </div>

          <div className="editor-identity-desc">
            {readOnly ? (
              script.setup.description ? (
                <p className="text-sm text-muted-foreground">{script.setup.description}</p>
              ) : null
            ) : (
              <Input
                value={script.setup.description}
                onChange={(e) => patchSetup({ description: e.target.value })}
                placeholder="Description"
                aria-label="Workflow description"
              />
            )}
          </div>

          <div className="editor-identity-phone">
            {readOnly ? (
              <span className="inline-flex min-h-9 items-center rounded-md bg-muted/80 px-2.5 text-sm">
                {script.setup.target || "No phone"}
              </span>
            ) : (
              <div className="min-w-0 flex-1 space-y-1">
                <Input
                  type="tel"
                  className={fieldErrorClass(phoneMissing)}
                  value={script.setup.target}
                  onChange={(e) => patchSetup({ target: e.target.value })}
                  placeholder="Phone number"
                  aria-label="Phone to call"
                  aria-invalid={phoneMissing}
                />
                {phoneMissing && (
                  <p className="text-xs text-destructive">Add a phone number to call.</p>
                )}
              </div>
            )}
            {onTest && (
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Button
                      type="button"
                      size="icon"
                      onClick={onTest}
                      aria-label="Run"
                      className="shrink-0"
                    >
                      <Play />
                    </Button>
                  }
                />
                <TooltipContent>Run</TooltipContent>
              </Tooltip>
            )}
          </div>
        </header>

        <div className="editor-body editor-workspace">
          <section className="editor-script-column space-y-2">
            <div className="editor-rail-head">
              <h2 className="text-sm font-bold tracking-tight">Call script</h2>
              <p className="text-xs text-muted-foreground">
                Ordered Steps Pathline follows on the call. Edits save when a Step is valid.
              </p>
            </div>

            <div className="flex flex-col gap-2">
              {visibleRules.map((rule, index) => (
                <InlineStepRow
                  key={rule.id}
                  step={rule}
                  stepNumber={index + 1}
                  existingLabels={stepLabels}
                  onSave={handleSaveStep}
                  onRemove={readOnly ? undefined : () => removeStep(rule, index + 1)}
                  onDuplicate={readOnly ? undefined : () => duplicateStep(rule, index)}
                  onMoveUp={readOnly ? undefined : () => moveStep(index, index - 1)}
                  onMoveDown={readOnly ? undefined : () => moveStep(index, index + 1)}
                  onMove={readOnly ? undefined : moveStep}
                  dragIndex={index}
                  canMoveUp={!readOnly && index > 0}
                  canMoveDown={!readOnly && index < visibleRules.length - 1}
                  readOnly={readOnly}
                />
              ))}
            </div>

            {visibleRules.length === 0 && !addingStep && (
              <p className={`field-hint text-xs ${needsSteps ? "text-destructive" : ""}`}>
                {needsSteps
                  ? "Add at least one Step to define the call flow."
                  : "No Steps yet. Add your first Step."}
              </p>
            )}

            {needsEndCall && visibleRules.length > 0 && (
              <p className="text-xs text-destructive" role="status">
                Add a Terminate Call Step so the Run can hang up cleanly.
              </p>
            )}

            {!readOnly && !addingStep && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="editor-table-add"
                onClick={() => setAddingStep(true)}
              >
                + Add Step
              </Button>
            )}

            {!readOnly && addingStep && (
              <InlineStepRow
                key="new-step"
                stepNumber={visibleRules.length + 1}
                existingLabels={stepLabels}
                onSave={handleSaveStep}
                onCancel={() => setAddingStep(false)}
              />
            )}
          </section>

          <div className="editor-inspector-stack">
            <aside className="editor-inspector-card">
              <div className="editor-rail-head">
                <h2 className="text-sm font-bold tracking-tight">Secrets</h2>
                <p className="text-xs text-muted-foreground">
                  Runtime values only — not saved with the Workflow.
                </p>
              </div>
              {inputVariables.length === 0 ? (
                <p className="field-hint text-xs">
                  None yet. Type a name in Press Keys (auto-wrapped as {"{{name}}"}).
                </p>
              ) : (
                <div className="space-y-2">
                  {inputVariables.map((name) => (
                    <label key={name} className="block space-y-1">
                      <code className="editor-var-token">{formatOutputDisplay(name)}</code>
                      <Input
                        type="password"
                        value={secrets[name] ?? ""}
                        onChange={(e) => patchSecret(name, e.target.value)}
                        placeholder="••••••••"
                        autoComplete="off"
                        disabled={readOnly}
                        className="h-9 font-mono tracking-widest"
                      />
                    </label>
                  ))}
                </div>
              )}
              {inputSyncIssues.map((issue) => (
                <p key={issue} className="text-xs text-destructive" role="alert">
                  {issue}
                </p>
              ))}
            </aside>

            <aside className="editor-inspector-card">
              <div className="editor-rail-head">
                <h2 className="text-sm font-bold tracking-tight">Rules</h2>
                <p className="text-xs text-muted-foreground">
                  Heard phrases that map to captured status fields.
                </p>
              </div>
              {runRules.length === 0 ? (
                <p className="field-hint text-xs">
                  None yet. Use Store Variable to capture {"{{card_status}}"}.
                </p>
              ) : (
                <div className="space-y-3">
                  {runRules.map((rule) => {
                    const phrases = splitPhrases(rule.when);
                    const outputLabel = formatOutputDisplay(rule.output);
                    return (
                      <div key={rule.id} className="space-y-1.5 rounded-md border border-border/80 p-2">
                        <Tooltip>
                          <TooltipTrigger
                            render={
                              <code className="editor-var-token block max-w-full whitespace-normal break-all">
                                {outputLabel}
                              </code>
                            }
                          />
                          <TooltipContent>{outputLabel}</TooltipContent>
                        </Tooltip>
                        <p className="text-[11px] text-muted-foreground break-all" title={rule.label}>
                          {rule.label}
                        </p>
                        {phrases.length === 0 ? (
                          <p className="text-xs text-muted-foreground">Open capture</p>
                        ) : (
                          <ul className="space-y-1">
                            {phrases.map((phrase, index) => (
                              <li key={`${rule.id}-${index}`}>
                                {readOnly ? (
                                  <p className="text-xs break-words">{phrase}</p>
                                ) : (
                                  <Input
                                    className="h-8 text-xs"
                                    value={phrase}
                                    aria-label={`${rule.output} phrase ${index + 1}`}
                                    onChange={(e) => {
                                      const next = [...phrases];
                                      next[index] = e.target.value;
                                      updateRunRulePhrases(rule.id, next);
                                    }}
                                    onBlur={() =>
                                      updateRunRulePhrases(
                                        rule.id,
                                        phrases.map((p) => p.trim()).filter(Boolean)
                                      )
                                    }
                                  />
                                )}
                              </li>
                            ))}
                          </ul>
                        )}
                        {!readOnly && phrases.length > 0 && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-[11px]"
                            onClick={() => updateRunRulePhrases(rule.id, [...phrases, ""])}
                          >
                            + Phrase
                          </Button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </aside>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
