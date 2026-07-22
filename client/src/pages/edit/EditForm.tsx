import { useState } from "react";
import { ChevronDown, ChevronRight, Copy, Download, Trash2 } from "lucide-react";
import type { Step, PathDocument } from "../../script/types";
import { extractVariableNames, withSyncedRules } from "../../script/compile";
import { scriptDisplayName } from "../../script/storage";
import {
  getPathReadiness,
  getWorkflowSetupIssues,
  READINESS_LABEL,
} from "../../script/pathReadiness";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InlineStepRow } from "./InlineStepRow";
import { isPlaceholderRule } from "../../script/ruleIntent";

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
  const [setupOpen, setSetupOpen] = useState(
    () => !script.setup.target.trim() || !script.setup.name.trim()
  );

  const patchSetup = (patch: Partial<PathDocument["setup"]>) =>
    onPatch({ setup: { ...script.setup, ...patch } });

  const inputVariables = extractVariableNames(script);
  const visibleRules = script.steps.filter((r) => !isPlaceholderRule(r));
  const stepLabels = visibleRules.map((item) => item.label);
  const readiness = getPathReadiness(script);
  const setupIssues = getWorkflowSetupIssues(script);

  const setupSummary = [
    script.setup.target.trim() || "No phone",
    `${Math.round(script.setup.timeoutMs / 1000)}s wait`,
    script.setup.description.trim() || null,
  ]
    .filter(Boolean)
    .join(" · ");

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

  return (
    <div className="script-editor-panel">
      {readOnly && (
        <div className="bundled-banner">
          Example Workflow (read-only).{" "}
          <Button type="button" variant="secondary" size="sm" onClick={onDuplicate}>
            Duplicate to edit
          </Button>
        </div>
      )}

      <header className="editor-topbar script-header">
        <div className="script-header-main min-w-0 flex-1">
          <div className="script-header-eyebrow-row">
            <p className="editor-eyebrow">Workflow</p>
            <Badge variant={readinessBadgeVariant(readiness)}>{READINESS_LABEL[readiness]}</Badge>
          </div>
          {readOnly ? (
            <h1 className="editor-title">{scriptDisplayName(script)}</h1>
          ) : (
            <Input
              className="script-header-name"
              value={script.setup.name}
              onChange={(e) => patchSetup({ name: e.target.value })}
              placeholder="Untitled Workflow"
              aria-label="Workflow name"
            />
          )}

          <div className="mt-3">
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-md px-1 py-1 text-left text-sm text-muted-foreground hover:text-foreground"
              onClick={() => setSetupOpen((open) => !open)}
              aria-expanded={setupOpen}
            >
              {setupOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
              <span className="font-medium text-foreground">Dial settings</span>
              {!setupOpen && <span className="truncate text-xs">{setupSummary}</span>}
            </button>

            {setupOpen && (
              <div className="script-header-meta mt-2">
                <label className="script-header-field">
                  <span>Description</span>
                  <Input
                    value={script.setup.description}
                    onChange={(e) => patchSetup({ description: e.target.value })}
                    disabled={readOnly}
                    placeholder="What this Workflow does"
                  />
                </label>
                <label className="script-header-field">
                  <span>Phone to call</span>
                  <Input
                    type="tel"
                    value={script.setup.target}
                    onChange={(e) => patchSetup({ target: e.target.value })}
                    disabled={readOnly}
                    placeholder="+1 (800) XXX-XXXX"
                  />
                </label>
                <label className="script-header-field script-header-field-narrow">
                  <span>Max wait between prompts</span>
                  <div className="script-header-timeout">
                    <Input
                      type="number"
                      value={Math.round(script.setup.timeoutMs / 1000)}
                      onChange={(e) => patchSetup({ timeoutMs: Number(e.target.value) * 1000 })}
                      disabled={readOnly}
                      min={1}
                    />
                    <span className="wait-suffix">sec</span>
                  </div>
                </label>
              </div>
            )}
          </div>
        </div>
        <div className="script-header-actions">
          {onTest && (
            <Button type="button" size="sm" onClick={onTest}>
              Run
            </Button>
          )}
          <div className="script-header-overflow">
            <Button type="button" variant="secondary" size="sm" onClick={onDuplicate}>
              <Copy />
              Duplicate
            </Button>
            {onExport && (
              <Button type="button" variant="secondary" size="sm" onClick={onExport}>
                <Download />
                Export
              </Button>
            )}
            {onDelete && (
              <Button type="button" variant="destructive" size="sm" onClick={onDelete}>
                <Trash2 />
                Delete
              </Button>
            )}
          </div>
        </div>
      </header>

      <div className="editor-body">
        {readiness === "needs-setup" && setupIssues.length > 0 && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/8 px-4 py-3">
            <p className="text-sm font-medium">Finish setup before running</p>
            <ul className="mt-1 list-disc pl-5 text-sm text-muted-foreground">
              {setupIssues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          </div>
        )}

        <section className="space-y-3">
          <div>
            <h2 className="text-base font-bold tracking-tight">Call script</h2>
            <p className="text-sm text-muted-foreground">
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
                onMoveUp={readOnly ? undefined : () => moveStep(index, index - 1)}
                onMoveDown={readOnly ? undefined : () => moveStep(index, index + 1)}
                canMoveUp={!readOnly && index > 0}
                canMoveDown={!readOnly && index < visibleRules.length - 1}
                readOnly={readOnly}
              />
            ))}
          </div>

          {visibleRules.length === 0 && !addingStep && (
            <p className="field-hint">No Steps yet. Add your first Step to define the call flow.</p>
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

        <section className="space-y-2 border-t border-border pt-4">
          <div>
            <h2 className="text-base font-bold tracking-tight">Run inputs (from Steps)</h2>
            <p className="text-sm text-muted-foreground">
              Values you enter when you Run — never stored with the Workflow.
            </p>
          </div>
          {inputVariables.length === 0 ? (
            <p className="field-hint">
              None yet. Use {"{{name}}"} in Press keys to add an Input.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {inputVariables.map((name) => (
                <Badge key={name} variant="outline" className="font-mono">
                  {name}
                </Badge>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
