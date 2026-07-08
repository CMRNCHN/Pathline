import type { FlowAction, FlowStep, IvrRule, ScriptDocument } from "../../script/types";
import {
  extractOutputRules,
  formatVariableRef,
  newFlowStep,
  newIvrRule,
} from "../../script/compile";
import { IVR_EXECUTION_RULES } from "../../script/types";
import { scriptDisplayName } from "../../script/storage";
import { SectionBlock } from "../../components/ui/SectionBlock";

const FLOW_ACTIONS: { value: FlowAction; label: string }[] = [
  { value: "trigger", label: "Trigger" },
  { value: "extract", label: "Extract" },
  { value: "validate", label: "Validate" },
  { value: "end", label: "End" },
  { value: "pass", label: "Pass" },
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
  const patchSetup = (patch: Partial<ScriptDocument["setup"]>) =>
    onPatch({ setup: { ...script.setup, ...patch } });

  const runtimeVariables = script.setup.runtimeVariables.filter(Boolean);
  const labeledRules = script.ivrRules.filter((r) => r.label.trim());
  const outputRules = extractOutputRules(script);

  const updateRules = (ivrRules: IvrRule[], conversationFlow?: FlowStep[]) =>
    onPatch(conversationFlow ? { ivrRules, conversationFlow } : { ivrRules });
  const updateFlow = (conversationFlow: FlowStep[]) => onPatch({ conversationFlow });

  const updateRuleAt = (index: number, patch: Partial<IvrRule>) => {
    const prev = script.ivrRules[index];
    const ivrRules = [...script.ivrRules];
    ivrRules[index] = { ...prev, ...patch };
    if (patch.label !== undefined && prev.label && patch.label !== prev.label) {
      const conversationFlow = script.conversationFlow.map((step) =>
        step.triggerLabel === prev.label ? { ...step, triggerLabel: patch.label } : step
      );
      updateRules(ivrRules, conversationFlow);
    } else {
      updateRules(ivrRules);
    }
  };

  const updateRuntimeVariables = (runtimeVariables: string[]) =>
    onPatch({ setup: { ...script.setup, runtimeVariables } });

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
        <h1 className="editor-title">{scriptDisplayName(script)}</h1>
        {onTest && (
          <button type="button" className="btn btn-accent btn-sm" onClick={onTest}>
            Run test
          </button>
        )}
      </header>

      <div className="editor-body">
        <SectionBlock
          index="01"
          title="Run Setup"
          description="Template defaults — target, timeout, speech preferences, and runtime variable names."
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
              <span>Timeout (seconds)</span>
              <input
                className="editor-input"
                type="number"
                value={Math.round(script.setup.timeoutMs / 1000)}
                onChange={(e) => patchSetup({ timeoutMs: Number(e.target.value) * 1000 })}
                disabled={readOnly}
              />
            </label>
            <label className="editor-field editor-field-check">
              <span>Auto-listen default</span>
              <input
                type="checkbox"
                checked={script.setup.speechPreferences.autoListen}
                onChange={(e) =>
                  patchSetup({
                    speechPreferences: { autoListen: e.target.checked },
                  })
                }
                disabled={readOnly}
              />
            </label>
          </div>

          <div className="editor-field editor-field-wide" style={{ marginTop: "1rem" }}>
            <span>Runtime variables</span>
            <p className="section-desc" style={{ marginBottom: "0.65rem" }}>
              Names for Run Configuration — referenced as {"{{name}}"} in IVR rules.
            </p>
            <div className="editor-table-wrap">
              <table className="editor-table">
                <thead>
                  <tr>
                    <th>Variable</th>
                    <th className="editor-table-col-actions" />
                  </tr>
                </thead>
                <tbody>
                  {script.setup.runtimeVariables.map((name, i) => (
                    <tr key={i} className="editor-table-row">
                      <td>
                        <input
                          className="editor-input mono"
                          value={name}
                          onChange={(e) => {
                            const runtimeVariables = [...script.setup.runtimeVariables];
                            runtimeVariables[i] = e.target.value.replace(/\s/g, "_");
                            updateRuntimeVariables(runtimeVariables);
                          }}
                          disabled={readOnly}
                          placeholder="card_number"
                        />
                      </td>
                      <td className="editor-table-actions">
                        {!readOnly && (
                          <button
                            type="button"
                            className="btn-icon"
                            onClick={() =>
                              updateRuntimeVariables(
                                script.setup.runtimeVariables.filter((_, j) => j !== i)
                              )
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
                onClick={() => updateRuntimeVariables([...script.setup.runtimeVariables, ""])}
              >
                + Variable
              </button>
            )}
          </div>
        </SectionBlock>

        <SectionBlock
          index="02"
          title="IVR Rules"
          description={
            <>
              What to do and what data comes back. Use <code className="mono">{"{{variable}}"}</code> in
              response — never literal secrets.
            </>
          }
          wide
        >
          {runtimeVariables.length === 0 && (
            <p className="field-hint warn" style={{ marginBottom: "0.75rem" }}>
              Add runtime variables in Run Setup before assigning response references.
            </p>
          )}
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Trigger</th>
                  <th>Response</th>
                  <th>Rule</th>
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
                        onChange={(e) => updateRuleAt(i, { label: e.target.value.replace(/\s/g, "_") })}
                        disabled={readOnly}
                        placeholder="claim_status_request"
                      />
                    </td>
                    <td>
                      <input
                        className="editor-input"
                        value={rule.trigger}
                        onChange={(e) => updateRuleAt(i, { trigger: e.target.value })}
                        disabled={readOnly}
                        placeholder="your claim number"
                      />
                    </td>
                    <td>
                      <select
                        className="editor-input mono"
                        value={rule.response}
                        onChange={(e) => updateRuleAt(i, { response: e.target.value })}
                        disabled={readOnly || runtimeVariables.length === 0}
                      >
                        <option value="">Select variable…</option>
                        {runtimeVariables.map((v) => (
                          <option key={v} value={formatVariableRef(v)}>
                            {formatVariableRef(v)}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        className="editor-input"
                        value={rule.rule}
                        onChange={(e) => updateRuleAt(i, { rule: e.target.value })}
                        disabled={readOnly}
                      >
                        {IVR_EXECUTION_RULES.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                        {!IVR_EXECUTION_RULES.includes(rule.rule as (typeof IVR_EXECUTION_RULES)[number]) &&
                          rule.rule && (
                            <option value={rule.rule}>{rule.rule}</option>
                          )}
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
                          onClick={() => updateRules(script.ivrRules.filter((r) => r.id !== rule.id))}
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
          title="Conversation Flow"
          description="When to execute rules — Detect, then Trigger, Extract, Validate, End, or Pass."
          wide
        >
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th className="editor-table-col-num">#</th>
                  <th>Detect</th>
                  <th className="editor-table-col-type">Action</th>
                  <th>Rule label</th>
                  <th className="editor-table-col-actions" />
                </tr>
              </thead>
              <tbody>
                {script.conversationFlow.map((step, i) => (
                  <FlowStepRow
                    key={step.id}
                    step={step}
                    index={i}
                    labeledRules={labeledRules}
                    outputRules={outputRules}
                    readOnly={readOnly}
                    onChange={(patch) => {
                      const conversationFlow = [...script.conversationFlow];
                      conversationFlow[i] = { ...step, ...patch };
                      updateFlow(conversationFlow);
                    }}
                    onRemove={() => updateFlow(script.conversationFlow.filter((s) => s.id !== step.id))}
                  />
                ))}
              </tbody>
            </table>
          </div>
          {!readOnly && (
            <button
              type="button"
              className="btn btn-secondary btn-sm editor-table-add"
              onClick={() => updateFlow([...script.conversationFlow, newFlowStep("trigger")])}
            >
              + Step
            </button>
          )}
        </SectionBlock>
      </div>
    </div>
  );
}

function FlowStepRow({
  step,
  index,
  labeledRules,
  outputRules,
  readOnly,
  onChange,
  onRemove,
}: {
  step: FlowStep;
  index: number;
  labeledRules: IvrRule[];
  outputRules: IvrRule[];
  readOnly: boolean;
  onChange: (patch: Partial<FlowStep>) => void;
  onRemove: () => void;
}) {
  const setAction = (action: FlowAction) => {
    const defaultLabel =
      action === "extract"
        ? outputRules[0]?.label ?? ""
        : action === "trigger"
          ? labeledRules[0]?.label ?? ""
          : undefined;
    onChange({
      action,
      triggerLabel: action === "trigger" || action === "extract" ? step.triggerLabel ?? defaultLabel : undefined,
    });
  };

  const ruleOptions = step.action === "extract" ? outputRules : labeledRules;

  return (
    <tr className="editor-table-row">
      <td className="editor-table-num">{index + 1}</td>
      <td>
        <input
          className="editor-input"
          value={step.detect}
          onChange={(e) => onChange({ detect: e.target.value })}
          placeholder="IVR phrase"
          disabled={readOnly}
        />
      </td>
      <td>
        <select
          className="editor-input editor-input-sm"
          value={step.action}
          onChange={(e) => setAction(e.target.value as FlowAction)}
          disabled={readOnly}
        >
          {FLOW_ACTIONS.map((a) => (
            <option key={a.value} value={a.value}>{a.label}</option>
          ))}
        </select>
      </td>
      <td>
        {step.action === "trigger" || step.action === "extract" ? (
          ruleOptions.length === 0 ? (
            <span className="field-hint warn">
              {step.action === "extract" ? "Set output on an IVR rule first" : "Add IVR rules first"}
            </span>
          ) : (
            <select
              className="editor-input"
              value={step.triggerLabel ?? ""}
              onChange={(e) => onChange({ triggerLabel: e.target.value })}
              disabled={readOnly}
            >
              <option value="">Select rule…</option>
              {ruleOptions.map((r) => (
                <option key={r.id} value={r.label}>
                  {r.label}
                  {step.action === "trigger" && r.response ? ` → ${r.response}` : ""}
                  {step.action === "extract" && r.output ? ` → ${r.output}` : ""}
                </option>
              ))}
            </select>
          )
        ) : (
          <span className="editor-table-dash">—</span>
        )}
      </td>
      <td className="editor-table-actions">
        {!readOnly && (
          <button type="button" className="btn-icon" onClick={onRemove} title="Remove">
            ×
          </button>
        )}
      </td>
    </tr>
  );
}
