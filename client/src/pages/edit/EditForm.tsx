import type { IvrRule, ScriptDocument } from "../../script/types";
import {
  extractOutputRules,
  formatVariableRef,
  newIvrRule,
  withSyncedRules,
} from "../../script/compile";
import { IVR_EXECUTION_RULES } from "../../script/types";
import { scriptDisplayName } from "../../script/storage";
import { SectionBlock } from "../../components/ui/SectionBlock";

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
  const patchSetup = (patch: Partial<ScriptDocument["setup"]>) =>
    onPatch({ setup: { ...script.setup, ...patch } });

  const outputRules = extractOutputRules(script);
  const runtimeVariables = script.setup.runtimeVariables.filter(Boolean);

  const updateRules = (ivrRules: IvrRule[]) => onPatch(withSyncedRules(script, ivrRules));

  const updateRuleAt = (index: number, patch: Partial<IvrRule>) => {
    const ivrRules = [...script.ivrRules];
    ivrRules[index] = { ...ivrRules[index], ...patch };
    updateRules(ivrRules);
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

      <header className="editor-topbar">
        <div>
          <p className="editor-eyebrow">RUN</p>
          <h1 className="editor-title">{scriptDisplayName(script)}</h1>
        </div>
        {onTest && (
          <button type="button" className="btn btn-accent btn-sm" onClick={onTest}>
            Run test
          </button>
        )}
      </header>

      <div className="editor-model-strip" aria-label="Run structure">
        <div className="editor-model-card">
          <span className="editor-model-index">Setup</span>
          <strong>Name · Target · Description · Timeout</strong>
        </div>
        <div className="editor-model-card editor-model-card-accent">
          <span className="editor-model-index">Rules</span>
          <strong>Label · Trigger · Response · Execution · Output</strong>
        </div>
        <div className="editor-model-card">
          <span className="editor-model-index">Results</span>
          <strong>Collected outputs</strong>
        </div>
      </div>

      <div className="editor-body">
        <SectionBlock index="01" title="Setup" description="Run defaults for this template.">
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
            <p className="field-hint" style={{ marginTop: 0 }}>
              Derived from <code className="mono">{"{{variable}}"}</code> references in rule responses. Values are set at run time.
            </p>
            {runtimeVariables.length === 0 ? (
              <p className="field-hint">Add a variable reference to a rule response to define one.</p>
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
        </SectionBlock>

        <SectionBlock
          index="02"
          title="Rules"
          description={
            <>
              Each rule defines what to listen for and how to respond. Use{" "}
              <code className="mono">{"{{variable}}"}</code> in response for run-time values.
            </>
          }
          wide
        >
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Trigger</th>
                  <th>Response</th>
                  <th>Execution rule</th>
                  <th>Output</th>
                  <th className="editor-table-col-actions" />
                </tr>
              </thead>
              <tbody>
                {script.ivrRules.map((rule, i) => (
                  <tr key={rule.id} className="editor-table-row">
                    <td>
                      <input
                        className="editor-input mono"
                        value={rule.label}
                        onChange={(e) =>
                          updateRuleAt(i, { label: e.target.value.replace(/\s/g, "_") })
                        }
                        disabled={readOnly}
                        placeholder="submit_account"
                      />
                    </td>
                    <td>
                      <input
                        className="editor-input"
                        value={rule.trigger}
                        onChange={(e) => updateRuleAt(i, { trigger: e.target.value })}
                        disabled={readOnly}
                        placeholder="account number"
                      />
                    </td>
                    <td>
                      {runtimeVariables.length > 0 ? (
                        <select
                          className="editor-input mono"
                          value={rule.response}
                          onChange={(e) => updateRuleAt(i, { response: e.target.value })}
                          disabled={readOnly}
                        >
                          <option value="">—</option>
                          {runtimeVariables.map((v) => (
                            <option key={v} value={formatVariableRef(v)}>
                              {formatVariableRef(v)}
                            </option>
                          ))}
                          {!runtimeVariables.some(
                            (v) => formatVariableRef(v) === rule.response
                          ) &&
                            rule.response && (
                              <option value={rule.response}>{rule.response}</option>
                            )}
                        </select>
                      ) : (
                        <input
                          className="editor-input mono"
                          value={rule.response}
                          onChange={(e) => updateRuleAt(i, { response: e.target.value })}
                          disabled={readOnly}
                          placeholder="{{variable}}"
                        />
                      )}
                    </td>
                    <td>
                      <select
                        className="editor-input"
                        value={rule.rule}
                        onChange={(e) => updateRuleAt(i, { rule: e.target.value })}
                        disabled={readOnly}
                      >
                        {IVR_EXECUTION_RULES.map((r) => (
                          <option key={r} value={r}>
                            {r}
                          </option>
                        ))}
                        {!IVR_EXECUTION_RULES.includes(
                          rule.rule as (typeof IVR_EXECUTION_RULES)[number]
                        ) &&
                          rule.rule && <option value={rule.rule}>{rule.rule}</option>}
                      </select>
                    </td>
                    <td>
                      <input
                        className="editor-input mono"
                        value={rule.output}
                        onChange={(e) =>
                          updateRuleAt(i, { output: e.target.value.replace(/\s/g, "_") })
                        }
                        disabled={readOnly}
                        placeholder="claim_status"
                      />
                    </td>
                    <td className="editor-table-actions">
                      {!readOnly && (
                        <button
                          type="button"
                          className="btn-icon"
                          onClick={() =>
                            updateRules(script.ivrRules.filter((r) => r.id !== rule.id))
                          }
                        >
                          ×
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!readOnly && (
            <button
              type="button"
              className="btn btn-secondary btn-sm editor-table-add"
              onClick={() => updateRules([...script.ivrRules, newIvrRule(script.ivrRules.length + 1)])}
            >
              + Rule
            </button>
          )}
        </SectionBlock>

        <SectionBlock
          index="03"
          title="Results"
          description="Collected outputs — derived from rules with an output field. Populated at runtime."
        >
          {outputRules.length === 0 ? (
            <p className="results-empty">
              Set an output field on a capture rule to define a collected result.
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
        </SectionBlock>
      </div>
    </div>
  );
}
