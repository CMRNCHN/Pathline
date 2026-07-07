import type {
  ExtractMapEntry,
  FlowAction,
  FlowStep,
  IvrRule,
  ExtractedSchemaField,
  ScriptDocument,
  SchemaFieldType,
} from "../../script/types";
import {
  newFlowStep,
  newIvrRule,
  newMapEntry,
  newSchemaField,
} from "../../script/compile";
import { scriptDisplayName } from "../../script/storage";

const FLOW_ACTIONS: { value: FlowAction; label: string }[] = [
  { value: "trigger", label: "Trigger" },
  { value: "extract", label: "Extract" },
  { value: "end", label: "End" },
  { value: "pass", label: "Pass" },
];

const SCHEMA_TYPES: SchemaFieldType[] = ["text", "currency", "number"];

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

  const ruleLabels = script.ivrRules.map((r) => r.label).filter(Boolean);
  const schemaFields = script.extractedSchema.map((f) => f.field).filter(Boolean);

  const updateRules = (ivrRules: IvrRule[]) => onPatch({ ivrRules });
  const updateFlow = (conversationFlow: FlowStep[]) => onPatch({ conversationFlow });
  const updateSchema = (extractedSchema: ExtractedSchemaField[]) => onPatch({ extractedSchema });

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
          <button type="button" className="btn btn-primary btn-sm" onClick={onTest}>
            Test
          </button>
        )}
      </header>

      <div className="editor-body">
        <section className="editor-section">
          <h2 className="editor-section-heading">Script Setup</h2>
          <p className="editor-section-desc">Template defaults — target, timeout, and speech preferences.</p>
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
        </section>

        <section className="editor-section editor-section-wide">
          <h2 className="editor-section-heading">IVR Rules</h2>
          <p className="editor-section-desc">
            What to send. Use <code className="mono">{"{{variable}}"}</code> references — never literal secrets.
          </p>
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Value reference</th>
                  <th>Expected input</th>
                  <th>Rule</th>
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
                        onChange={(e) => {
                          const ivrRules = [...script.ivrRules];
                          ivrRules[i] = { ...rule, label: e.target.value };
                          updateRules(ivrRules);
                        }}
                        disabled={readOnly}
                        placeholder="cc_num_request"
                      />
                    </td>
                    <td>
                      <input
                        className="editor-input mono"
                        value={rule.valueReference}
                        onChange={(e) => {
                          const ivrRules = [...script.ivrRules];
                          ivrRules[i] = { ...rule, valueReference: e.target.value };
                          updateRules(ivrRules);
                        }}
                        disabled={readOnly}
                        placeholder="{{card_number}}"
                      />
                    </td>
                    <td>
                      <input
                        className="editor-input"
                        value={rule.expectedInput}
                        onChange={(e) => {
                          const ivrRules = [...script.ivrRules];
                          ivrRules[i] = { ...rule, expectedInput: e.target.value };
                          updateRules(ivrRules);
                        }}
                        disabled={readOnly}
                      />
                    </td>
                    <td>
                      <input
                        className="editor-input"
                        value={rule.rule}
                        onChange={(e) => {
                          const ivrRules = [...script.ivrRules];
                          ivrRules[i] = { ...rule, rule: e.target.value };
                          updateRules(ivrRules);
                        }}
                        disabled={readOnly}
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
              onClick={() => updateRules([...script.ivrRules, newIvrRule()])}
            >
              + Rule
            </button>
          )}
        </section>

        <section className="editor-section editor-section-wide">
          <h2 className="editor-section-heading">Conversation Flow</h2>
          <p className="editor-section-desc">
            Detect → Trigger (IVR rule label) · Extract (schema field + map) · End · Pass.
          </p>
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th className="editor-table-col-num">#</th>
                  <th>Detect</th>
                  <th className="editor-table-col-type">Action</th>
                  <th>Target</th>
                  <th>Map</th>
                  <th className="editor-table-col-actions" />
                </tr>
              </thead>
              <tbody>
                {script.conversationFlow.map((step, i) => (
                  <FlowStepRow
                    key={step.id}
                    step={step}
                    index={i}
                    ruleLabels={ruleLabels}
                    schemaFields={schemaFields}
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
        </section>

        <section className="editor-section">
          <h2 className="editor-section-heading">Extracted Data Schema</h2>
          <p className="editor-section-desc">Fields the flow can populate at runtime.</p>
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Type</th>
                  <th className="editor-table-col-actions" />
                </tr>
              </thead>
              <tbody>
                {script.extractedSchema.map((field, i) => (
                  <tr key={field.id} className="editor-table-row">
                    <td>
                      <input
                        className="editor-input mono"
                        value={field.field}
                        onChange={(e) => {
                          const extractedSchema = [...script.extractedSchema];
                          extractedSchema[i] = { ...field, field: e.target.value };
                          updateSchema(extractedSchema);
                        }}
                        disabled={readOnly}
                        placeholder="claim_status"
                      />
                    </td>
                    <td>
                      <select
                        className="editor-input"
                        value={field.type}
                        onChange={(e) => {
                          const extractedSchema = [...script.extractedSchema];
                          extractedSchema[i] = {
                            ...field,
                            type: e.target.value as SchemaFieldType,
                          };
                          updateSchema(extractedSchema);
                        }}
                        disabled={readOnly}
                      >
                        {SCHEMA_TYPES.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </td>
                    <td className="editor-table-actions">
                      {!readOnly && (
                        <button
                          type="button"
                          className="btn-icon"
                          onClick={() =>
                            updateSchema(script.extractedSchema.filter((f) => f.id !== field.id))
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
              onClick={() => updateSchema([...script.extractedSchema, newSchemaField()])}
            >
              + Field
            </button>
          )}
        </section>
      </div>
    </div>
  );
}

function FlowStepRow({
  step,
  index,
  ruleLabels,
  schemaFields,
  readOnly,
  onChange,
  onRemove,
}: {
  step: FlowStep;
  index: number;
  ruleLabels: string[];
  schemaFields: string[];
  readOnly: boolean;
  onChange: (patch: Partial<FlowStep>) => void;
  onRemove: () => void;
}) {
  const setAction = (action: FlowAction) => {
    onChange({
      action,
      triggerLabel: action === "trigger" ? step.triggerLabel ?? ruleLabels[0] ?? "" : undefined,
      extractField: action === "extract" ? step.extractField ?? schemaFields[0] ?? "" : undefined,
      map: action === "extract" ? step.map ?? [newMapEntry()] : undefined,
    });
  };

  const updateMap = (map: ExtractMapEntry[]) => onChange({ map });

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
        {step.action === "trigger" && (
          <select
            className="editor-input"
            value={step.triggerLabel ?? ""}
            onChange={(e) => onChange({ triggerLabel: e.target.value })}
            disabled={readOnly}
          >
            <option value="">Label</option>
            {ruleLabels.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        )}
        {step.action === "extract" && (
          <select
            className="editor-input"
            value={step.extractField ?? ""}
            onChange={(e) => onChange({ extractField: e.target.value })}
            disabled={readOnly}
          >
            <option value="">Field</option>
            {schemaFields.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        )}
        {(step.action === "end" || step.action === "pass") && (
          <span className="editor-table-dash">—</span>
        )}
      </td>
      <td>
        {step.action === "extract" ? (
          <div className="flow-map-editor">
            {(step.map ?? []).map((entry, mi) => (
              <div key={entry.id} className="flow-map-row">
                <input
                  className="editor-input editor-input-sm"
                  value={entry.detect}
                  onChange={(e) => {
                    const map = [...(step.map ?? [])];
                    map[mi] = { ...entry, detect: e.target.value };
                    updateMap(map);
                  }}
                  placeholder="detect"
                  disabled={readOnly}
                />
                <span className="flow-map-arrow">→</span>
                <input
                  className="editor-input editor-input-sm"
                  value={entry.value}
                  onChange={(e) => {
                    const map = [...(step.map ?? [])];
                    map[mi] = { ...entry, value: e.target.value };
                    updateMap(map);
                  }}
                  placeholder="value"
                  disabled={readOnly}
                />
                {!readOnly && (
                  <button
                    type="button"
                    className="btn-icon"
                    onClick={() => updateMap((step.map ?? []).filter((m) => m.id !== entry.id))}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            {!readOnly && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => updateMap([...(step.map ?? []), newMapEntry()])}
              >
                + Map
              </button>
            )}
          </div>
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
