import { useState } from "react";
import { Copy, Download, Trash2 } from "lucide-react";
import type { Step, PathDocument } from "../../script/types";
import { extractVariableNames, withSyncedRules } from "../../script/compile";
import { scriptDisplayName } from "../../script/storage";
import { getPathReadiness, READINESS_LABEL } from "../../script/pathReadiness";
import { SectionBlock } from "../../components/ui/SectionBlock";
import { Badge } from "../../components/ui/Badge";
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
  const readinessVariant =
    readiness === "ready" ? "success" : readiness === "needs-setup" ? "warn" : "muted";
  const editingRule = editingRuleId
    ? script.steps.find((r) => r.id === editingRuleId)
    : undefined;

  const updateRules = (ivrRules: Step[]) => onPatch(withSyncedRules(script, ivrRules));

  const closeBuilder = () => {
    setBuilderOpen(false);
    setEditingRuleId(null);
  };

  const handleSaveRule = (rule: Step) => {
    const baseRules = script.steps.filter((r) => !isPlaceholderRule(r));
    const ivrRules = editingRuleId
      ? baseRules.map((r) => (r.id === editingRuleId ? rule : r))
      : [...baseRules, rule];
    updateRules(ivrRules);
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
          <button type="button" className="btn btn-sm btn-secondary" onClick={onDuplicate}>
            Duplicate to edit
          </button>
        </div>
      )}

      <header className="editor-topbar script-header">
        <div className="script-header-main">
          <div className="script-header-eyebrow-row">
            <p className="editor-eyebrow">Path</p>
            <Badge variant={readinessVariant}>{READINESS_LABEL[readiness]}</Badge>
          </div>
          {readOnly ? (
            <h1 className="editor-title">{scriptDisplayName(script)}</h1>
          ) : (
            <input
              className="editor-input script-header-name"
              value={script.setup.name}
              onChange={(e) => patchSetup({ name: e.target.value })}
              placeholder="Untitled Path"
              aria-label="Path name"
            />
          )}
          <div className="script-header-meta">
            <label className="script-header-field">
              <span>Description</span>
              <input
                className="editor-input"
                value={script.setup.description}
                onChange={(e) => patchSetup({ description: e.target.value })}
                disabled={readOnly}
                placeholder="What this Path does"
              />
            </label>
            <label className="script-header-field">
              <span>Target</span>
              <input
                className="editor-input"
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
                <input
                  className="editor-input"
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
            <button type="button" className="btn btn-accent btn-sm" onClick={onTest}>
              Run
            </button>
          )}
          <div className="script-header-overflow">
            <button type="button" className="btn btn-secondary btn-sm" onClick={onDuplicate}>
              <Copy size={14} />
              Duplicate
            </button>
            {onExport && (
              <button type="button" className="btn btn-secondary btn-sm" onClick={onExport}>
                <Download size={14} />
                Export
              </button>
            )}
            {onDelete && (
              <button type="button" className="btn btn-danger btn-sm" onClick={onDelete}>
                <Trash2 size={14} />
                Delete
              </button>
            )}
          </div>
        </div>
      </header>

      <div className="editor-body">
        <SectionBlock
          index="01"
          title="Steps"
          description="Each Step has a When (what starts it) and a Then (what Pathline does)."
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
            <button type="button" className="btn btn-secondary btn-sm editor-table-add" onClick={openAdd}>
              + Add Step
            </button>
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
