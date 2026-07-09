import { useState } from "react";
import type { IvrRule, ScriptDocument } from "../../script/types";
import { extractOutputRules, extractVariableNames, withSyncedRules } from "../../script/compile";
import { scriptDisplayName } from "../../script/storage";
import { SectionBlock } from "../../components/ui/SectionBlock";
import { RuleWizard } from "./ruleWizard/RuleWizard";
import { RuleCard } from "./RuleCard";
import { outputsSection } from "../../script/ruleCopy";
import { isPlaceholderRule } from "../../script/ruleIntent";

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
  const inputVariables = extractVariableNames(script);
  const visibleRules = script.ivrRules.filter((r) => !isPlaceholderRule(r));
  const editingRule = editingRuleId
    ? script.ivrRules.find((r) => r.id === editingRuleId)
    : undefined;

  const updateRules = (ivrRules: IvrRule[]) => onPatch(withSyncedRules(script, ivrRules));

  const closeBuilder = () => {
    setBuilderOpen(false);
    setEditingRuleId(null);
  };

  const handleSaveRule = (rule: IvrRule) => {
    const baseRules = script.ivrRules.filter((r) => !isPlaceholderRule(r));
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
          Example script (read-only).{" "}
          <button type="button" className="btn btn-sm btn-secondary" onClick={onDuplicate}>
            Duplicate
          </button>
        </div>
      )}

      <header className="editor-topbar script-header">
        <div className="script-header-main">
          <p className="editor-eyebrow">Script</p>
          {readOnly ? (
            <h1 className="editor-title">{scriptDisplayName(script)}</h1>
          ) : (
            <input
              className="editor-input script-header-name"
              value={script.setup.name}
              onChange={(e) => patchSetup({ name: e.target.value })}
              placeholder="Untitled script"
              aria-label="Script name"
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
                placeholder="What this script does"
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
          {!readOnly && <p className="script-header-status">Status: Draft</p>}
        </div>
        {onTest && (
          <button type="button" className="btn btn-accent btn-sm" onClick={onTest}>
            Run test
          </button>
        )}
      </header>

      <div className="editor-body">
        <SectionBlock
          index="01"
          title="Rules"
          description="Define what the assistant does when it hears the IVR."
          wide
        >
          <div className="rule-card-list">
            {visibleRules.map((rule) => (
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
              + Add rule
            </button>
          )}

          {!readOnly && builderOpen && (
            <RuleWizard
              key={editingRuleId ?? "new"}
              existingLabels={script.ivrRules.map((r) => r.label)}
              editingRule={editingRule}
              onSave={handleSaveRule}
              onCancel={closeBuilder}
            />
          )}
        </SectionBlock>

        <SectionBlock
          index="02"
          title={outputsSection.title}
          description={outputsSection.description}
        >
          {outputRules.length === 0 && inputVariables.length === 0 ? (
            <p className="field-hint">{outputsSection.empty}</p>
          ) : (
            <div className="outputs-block">
              {inputVariables.length > 0 && (
                <>
                  <h4 className="outputs-subtitle">{outputsSection.runValues}</h4>
                  <ul className="results-list">
                    {inputVariables.map((name) => (
                      <li key={name} className="results-list-item mono">
                        {name}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {outputRules.length > 0 && (
                <>
                  <h4 className="outputs-subtitle">{outputsSection.savedFromIvr}</h4>
                  <ul className="results-list">
                    {outputRules.map((rule) => (
                      <li key={rule.id} className="results-list-item mono">
                        {rule.output}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}
        </SectionBlock>
      </div>
    </div>
  );
}
