import { useState } from "react";
import type { IvrRule, ScriptDocument } from "../../script/types";
import { extractOutputRules, withSyncedRules } from "../../script/compile";
import { SectionBlock } from "../../components/ui/SectionBlock";
import { RuleBuilder } from "./RuleBuilder";
import { RuleCard } from "./RuleCard";

export interface EditFormProps {
  script: ScriptDocument;
  readOnly: boolean;
  onPatch: (patch: Partial<ScriptDocument>) => void;
  onDuplicate: () => void;
  onTest?: () => void;
}

export function EditForm({
  script,
  readOnly,
  onPatch,
  onDuplicate,
  onTest,
}: EditFormProps) {
  const [builderOpen, setBuilderOpen] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  const patchSetup = (patch: Partial<ScriptDocument["setup"]>) =>
    onPatch({ setup: { ...script.setup, ...patch } });

  const outputRules = extractOutputRules(script);
  const editingRule = editingRuleId
    ? script.ivrRules.find((r) => r.id === editingRuleId)
    : undefined;

  const updateRules = (ivrRules: IvrRule[]) => onPatch(withSyncedRules(script, ivrRules));

  const addVariable = (name: string) => {
    const runtimeVariables = [...new Set([...script.setup.runtimeVariables, name])].sort();
    onPatch({ setup: { ...script.setup, runtimeVariables } });
  };

  const closeBuilder = () => {
    setBuilderOpen(false);
    setEditingRuleId(null);
  };

  const handleSaveRule = (rule: IvrRule) => {
    const ivrRules = editingRuleId
      ? script.ivrRules.map((r) => (r.id === editingRuleId ? rule : r))
      : [...script.ivrRules, rule];
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
          Example script (read-only).{" "}
          <button type="button" className="btn btn-sm btn-secondary" onClick={onDuplicate}>
            Duplicate
          </button>
        </div>
      )}

      <div className="editor-body">
        <SectionBlock
          index="01"
          title="Setup"
          description="Defaults for this run template."
          heroTitle={
            <input
              className="editor-script-title"
              value={script.setup.name}
              onChange={(e) => patchSetup({ name: e.target.value })}
              disabled={readOnly}
              placeholder="Untitled"
              aria-label="Script name"
            />
          }
          actions={
            onTest ? (
              <button type="button" className="btn btn-accent btn-sm" onClick={onTest}>
                Run test
              </button>
            ) : undefined
          }
        >
          <div className="editor-field-grid">
            <label className="editor-field editor-field-wide">
              <span>Local intended file path</span>
              <input
                className="editor-input mono"
                value={script.setup.localPath}
                onChange={(e) => patchSetup({ localPath: e.target.value })}
                disabled={readOnly}
                placeholder="/path/to/script.json"
              />
            </label>
            <label className="editor-field">
              <span>Target</span>
              <input
                className="editor-input"
                type="tel"
                value={script.setup.target}
                onChange={(e) => patchSetup({ target: e.target.value })}
                disabled={readOnly}
              />
            </label>
            <label className="editor-field editor-field-wide">
              <span>Description</span>
              <input
                className="editor-input"
                value={script.setup.description}
                onChange={(e) => patchSetup({ description: e.target.value })}
                disabled={readOnly}
              />
            </label>
            <label className="editor-field">
              <span>Timeout (seconds)</span>
              <input
                className="editor-input"
                type="number"
                value={Math.round(script.setup.timeoutMs / 1000)}
                onChange={(e) => patchSetup({ timeoutMs: Number(e.target.value) * 1000 })}
                disabled={readOnly}
              />
            </label>
          </div>

          <div className="setup-values-block">
            <h4 className="setup-values-title">Run values</h4>
            <p className="section-desc">
              Names only — you fill in the real values when you start a run.
            </p>
            <div className="setup-values-list">
              {script.setup.runtimeVariables.map((name, i) => (
                <div key={i} className="setup-value-chip">
                  <input
                    className="editor-input mono setup-value-input"
                    value={name}
                    onChange={(e) => {
                      const runtimeVariables = [...script.setup.runtimeVariables];
                      runtimeVariables[i] = e.target.value.replace(/\s/g, "_");
                      patchSetup({ runtimeVariables });
                    }}
                    disabled={readOnly}
                    placeholder="customer_account"
                  />
                  {!readOnly && (
                    <button
                      type="button"
                      className="btn-icon"
                      onClick={() =>
                        patchSetup({
                          runtimeVariables: script.setup.runtimeVariables.filter((_, j) => j !== i),
                        })
                      }
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
            </div>
            {!readOnly && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() =>
                  patchSetup({ runtimeVariables: [...script.setup.runtimeVariables, ""] })
                }
              >
                + Run value
              </button>
            )}
          </div>
        </SectionBlock>

        <SectionBlock
          index="02"
          title="Steps"
          description="Tell the assistant what to do when it hears the IVR."
          wide
        >
          <div className="rule-card-list">
            {script.ivrRules.map((rule) => (
              <RuleCard
                key={rule.id}
                rule={rule}
                readOnly={readOnly}
                onEdit={() => openEdit(rule.id)}
                onRemove={() => updateRules(script.ivrRules.filter((r) => r.id !== rule.id))}
              />
            ))}
          </div>

          {!readOnly && !builderOpen && (
            <button type="button" className="btn btn-secondary btn-sm editor-table-add" onClick={openAdd}>
              + Add step
            </button>
          )}

          {!readOnly && builderOpen && (
            <RuleBuilder
              runtimeVariables={script.setup.runtimeVariables.filter(Boolean)}
              existingLabels={script.ivrRules.map((r) => r.label)}
              editingRule={editingRule}
              onAddVariable={addVariable}
              onSave={handleSaveRule}
              onCancel={closeBuilder}
            />
          )}
        </SectionBlock>

        <SectionBlock
          index="03"
          title="Results"
          description="Information captured during the call — defined by your capture steps."
        >
          {outputRules.length === 0 ? (
            <p className="field-hint">Add a capture step to collect information from the IVR.</p>
          ) : (
            <ul className="results-list">
              {outputRules.map((rule) => (
                <li key={rule.id} className="results-list-item mono">
                  {rule.output}
                </li>
              ))}
            </ul>
          )}
        </SectionBlock>
      </div>
    </div>
  );
}
