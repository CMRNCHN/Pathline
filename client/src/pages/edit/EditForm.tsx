import { useRef, useState } from "react";
import type { IvrRule, ScriptDocument } from "../../script/types";
import { extractOutputRules, formatVariableRef, withSyncedRules } from "../../script/compile";
import { scriptDisplayName } from "../../script/storage";
import { RuleBuilder } from "./RuleBuilder";
import { RuleCard } from "./RuleCard";

type RunSectionId = "setup" | "rules" | "results";

const RUN_SECTIONS: {
  id: RunSectionId;
  index: string;
  title: string;
  summary: string;
}[] = [
  {
    id: "setup",
    index: "01",
    title: "Setup",
    summary: "Name · Target · Description · Timeout",
  },
  {
    id: "rules",
    index: "02",
    title: "Rules",
    summary: "Navigate · Capture · Wait · End",
  },
  {
    id: "results",
    index: "03",
    title: "Results",
    summary: "Collected outputs",
  },
];

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
  const [activeSection, setActiveSection] = useState<RunSectionId>("setup");
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);
  const sectionRefs = useRef<Record<RunSectionId, HTMLElement | null>>({
    setup: null,
    rules: null,
    results: null,
  });

  const patchSetup = (patch: Partial<ScriptDocument["setup"]>) =>
    onPatch({ setup: { ...script.setup, ...patch } });

  const outputRules = extractOutputRules(script);
  const runtimeVariables = script.setup.runtimeVariables.filter(Boolean);

  const updateRules = (ivrRules: IvrRule[]) => onPatch(withSyncedRules(script, ivrRules));

  const editingRule = editingRuleId
    ? script.ivrRules.find((r) => r.id === editingRuleId)
    : undefined;

  const openNewStep = () => {
    setEditingRuleId(null);
    setShowBuilder(true);
  };

  const openEditStep = (ruleId: string) => {
    setEditingRuleId(ruleId);
    setShowBuilder(true);
  };

  const closeBuilder = () => {
    setShowBuilder(false);
    setEditingRuleId(null);
  };

  const saveRule = (rule: IvrRule) => {
    const exists = script.ivrRules.some((r) => r.id === rule.id);
    const ivrRules = exists
      ? script.ivrRules.map((r) => (r.id === rule.id ? rule : r))
      : [...script.ivrRules, rule];
    updateRules(ivrRules);
    closeBuilder();
  };

  const removeRule = (ruleId: string) => {
    updateRules(script.ivrRules.filter((r) => r.id !== ruleId));
    if (editingRuleId === ruleId) closeBuilder();
  };

  const addVariable = (name: string) => {
    const normalized = name.replace(/\s/g, "_").trim();
    if (!normalized) return;
    const runtimeVariables = [...new Set([...script.setup.runtimeVariables, normalized])].sort();
    onPatch({ setup: { ...script.setup, runtimeVariables } });
  };

  const ruleCount = script.ivrRules.length;
  const outputCount = outputRules.length;

  const sectionMeta: Record<RunSectionId, string> = {
    setup: `${runtimeVariables.length} variable${runtimeVariables.length === 1 ? "" : "s"}`,
    rules: `${ruleCount} step${ruleCount === 1 ? "" : "s"}`,
    results: `${outputCount} field${outputCount === 1 ? "" : "s"}`,
  };

  const jumpToSection = (id: RunSectionId) => {
    setActiveSection(id);
    sectionRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="script-editor-panel">
      {readOnly && (
        <div className="bundled-banner">
          <span>Example template (read-only).</span>
          <button type="button" className="btn btn-sm btn-secondary" onClick={onDuplicate}>
            Duplicate to edit
          </button>
        </div>
      )}

      <header className="editor-topbar">
        <div className="editor-topbar-main">
          <p className="editor-eyebrow">RUN template</p>
          <h1 className="editor-title">{scriptDisplayName(script)}</h1>
          {script.setup.description && (
            <p className="editor-subtitle">{script.setup.description}</p>
          )}
        </div>
        {onTest && (
          <div className="editor-topbar-actions">
            <button type="button" className="btn btn-accent btn-sm" onClick={onTest}>
              Run test
            </button>
          </div>
        )}
      </header>

      <nav className="editor-model-strip" aria-label="Run structure">
        {RUN_SECTIONS.map((section) => (
          <button
            key={section.id}
            id={`run-nav-${section.id}`}
            type="button"
            className={`editor-model-card${
              activeSection === section.id ? " editor-model-card-active" : ""
            }`}
            onClick={() => jumpToSection(section.id)}
            aria-current={activeSection === section.id ? "true" : undefined}
          >
            <span className="editor-model-index">
              {section.index} · {section.title}
            </span>
            <strong>{section.summary}</strong>
            <span className="editor-model-meta">{sectionMeta[section.id]}</span>
          </button>
        ))}
      </nav>

      <div className="editor-body">
        <section
          id="run-setup"
          ref={(el) => {
            sectionRefs.current.setup = el;
          }}
          className="editor-section"
          aria-labelledby="run-nav-setup"
        >
          <div className="editor-field-grid">
            <label className="editor-field">
              <span>Name</span>
              <input
                className="editor-input"
                value={script.setup.name}
                onChange={(e) => patchSetup({ name: e.target.value })}
                disabled={readOnly}
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
              <span>Timeout</span>
              <input
                className="editor-input"
                type="number"
                min={1}
                value={Math.round(script.setup.timeoutMs / 1000)}
                onChange={(e) => patchSetup({ timeoutMs: Number(e.target.value) * 1000 })}
                disabled={readOnly}
              />
              <span className="field-hint">seconds</span>
            </label>
          </div>

          <div className="setup-values-block">
            <p className="setup-values-title">Runtime variables</p>
            <p className="setup-values-hint">
              Names you use in navigate steps. Values are filled in at run configuration.
            </p>
            {runtimeVariables.length === 0 ? (
              <p className="results-empty">Add a step that uses a run-time value to define one.</p>
            ) : (
              <div className="runtime-vars-row">
                {runtimeVariables.map((name) => (
                  <span key={name} className="runtime-var-chip">
                    {formatVariableRef(name)}
                  </span>
                ))}
              </div>
            )}
          </div>
        </section>

        <section
          id="run-rules"
          ref={(el) => {
            sectionRefs.current.rules = el;
          }}
          className="editor-section editor-section-wide"
          aria-labelledby="run-nav-rules"
        >
          {script.ivrRules.length > 0 && (
            <ol className="rule-card-list">
              {script.ivrRules.map((rule) => (
                <li key={rule.id}>
                  <RuleCard
                    rule={rule}
                    readOnly={readOnly}
                    onEdit={() => openEditStep(rule.id)}
                    onRemove={() => removeRule(rule.id)}
                  />
                </li>
              ))}
            </ol>
          )}

          {script.ivrRules.length === 0 && !showBuilder && (
            <p className="results-empty">
              No steps yet. Add your first step — you&apos;ll answer a few short questions for each one.
            </p>
          )}

          {!readOnly && showBuilder && (
            <RuleBuilder
              runtimeVariables={runtimeVariables}
              existingLabels={script.ivrRules.map((r) => r.label)}
              editingRule={editingRule}
              onAddVariable={addVariable}
              onSave={saveRule}
              onCancel={closeBuilder}
            />
          )}

          {!readOnly && !showBuilder && (
            <button type="button" className="btn btn-secondary btn-sm editor-table-add" onClick={openNewStep}>
              + Add step
            </button>
          )}
        </section>

        <section
          id="run-results"
          ref={(el) => {
            sectionRefs.current.results = el;
          }}
          className="editor-section"
          aria-labelledby="run-nav-results"
        >
          {outputRules.length === 0 ? (
            <p className="results-empty">
              Add a capture step to define what this template collects at runtime.
            </p>
          ) : (
            <ul className="results-list">
              {outputRules.map((rule) => (
                <li key={rule.id} className="results-list-item mono">
                  {rule.output}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
