import { useState } from "react";
import { Copy, Download, Trash2 } from "lucide-react";
import type { Step, PathDocument } from "../../script/types";
import { extractVariableNames, withSyncedRules } from "../../script/compile";
import { scriptDisplayName } from "../../script/storage";
import { getPathReadiness, READINESS_LABEL } from "../../script/pathReadiness";
import { SectionBlock } from "../../components/ui/SectionBlock";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RuleWizard } from "./ruleWizard/RuleWizard";
import { RuleCard } from "./RuleCard";
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
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  const patchSetup = (patch: Partial<PathDocument["setup"]>) =>
    onPatch({ setup: { ...script.setup, ...patch } });

  const inputVariables = extractVariableNames(script);
  const visibleRules = script.steps.filter((r) => !isPlaceholderRule(r));
  const readiness = getPathReadiness(script);
  const editingRule = editingRuleId
    ? script.steps.find((r) => r.id === editingRuleId)
    : undefined;

  const updateRules = (steps: Step[]) => onPatch(withSyncedRules(script, steps));

  const closeBuilder = () => {
    setBuilderOpen(false);
    setEditingRuleId(null);
  };

  const handleSaveRule = (rule: Step) => {
    const baseRules = script.steps.filter((r) => !isPlaceholderRule(r));
    const steps = editingRuleId
      ? baseRules.map((r) => (r.id === editingRuleId ? rule : r))
      : [...baseRules, rule];
    updateRules(steps);
    closeBuilder();
  };

  const openAdd = () => {
    setEditingRuleId(null);
    setBuilderOpen(true);
  };

  const openEdit = (id: string) => {
    setEditingRuleId(id);
    setBuilderOpen(true);
  };

  return (
    <div className="script-editor-panel">
      {readOnly && (
        <div className="bundled-banner">
          Example Path (read-only).{" "}
          <Button type="button" variant="secondary" size="sm" onClick={onDuplicate}>
            Duplicate to edit
          </Button>
        </div>
      )}

      <header className="editor-topbar script-header">
        <div className="script-header-main">
          <div className="script-header-eyebrow-row">
            <p className="editor-eyebrow">Path</p>
            <Badge variant={readinessBadgeVariant(readiness)}>{READINESS_LABEL[readiness]}</Badge>
          </div>
          {readOnly ? (
            <h1 className="editor-title">{scriptDisplayName(script)}</h1>
          ) : (
            <Input
              className="script-header-name"
              value={script.setup.name}
              onChange={(e) => patchSetup({ name: e.target.value })}
              placeholder="Untitled Path"
              aria-label="Path name"
            />
          )}
          <div className="script-header-meta">
            <label className="script-header-field">
              <span>Description</span>
              <Input
                value={script.setup.description}
                onChange={(e) => patchSetup({ description: e.target.value })}
                disabled={readOnly}
                placeholder="What this Path does"
              />
            </label>
            <label className="script-header-field">
              <span>Target</span>
              <Input
                type="tel"
                value={script.setup.target}
                onChange={(e) => patchSetup({ target: e.target.value })}
                disabled={readOnly}
                placeholder="+1 (800) XXX-XXXX"
              />
            </label>
            <label className="script-header-field script-header-field-narrow">
              <span>Timeout</span>
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
        <SectionBlock
          index="01"
          title="Steps"
          description="Each Step has a When (what starts it) and a Then (what PromptPath does)."
          wide
        >
          <div className="rule-card-list">
            {visibleRules.map((rule) => (
              <RuleCard
                key={rule.id}
                rule={rule}
                readOnly={readOnly}
                onEdit={() => openEdit(rule.id)}
                onRemove={() => updateRules(script.steps.filter((r) => r.id !== rule.id))}
              />
            ))}
          </div>

          {visibleRules.length === 0 && !builderOpen && (
            <p className="field-hint">No Steps yet. Add your first Step to define the call flow.</p>
          )}

          {!readOnly && !builderOpen && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="editor-table-add"
              onClick={openAdd}
            >
              + Add Step
            </Button>
          )}

          {!readOnly && builderOpen && (
            <RuleWizard
              key={editingRuleId ?? "new"}
              existingLabels={script.steps.map((r) => r.label)}
              editingRule={editingRule}
              onSave={handleSaveRule}
              onCancel={closeBuilder}
            />
          )}
        </SectionBlock>

        <SectionBlock
          index="02"
          title="Inputs"
          description="Values you provide when you Run this Path — never stored with the Path."
        >
          {inputVariables.length === 0 ? (
            <p className="field-hint">
              No Inputs required. Add a Step that submits a value and its Input appears here.
            </p>
          ) : (
            <ul className="results-list">
              {inputVariables.map((name) => (
                <li key={name} className="results-list-item mono">
                  {name}
                </li>
              ))}
            </ul>
          )}
        </SectionBlock>
      </div>
    </div>
  );
}
