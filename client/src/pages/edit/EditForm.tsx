import type { ConversationStep, ScriptDocument } from "../../script/types";
import { newConversationStep, newResult, newSecret } from "../../script/compile";

type StepKind = "navigate" | "extract" | "end";

function stepKind(step: ConversationStep): StepKind {
  if (step.action === "hang_up") return "end";
  if (step.action === "save_value") return "extract";
  return "navigate";
}

function FlowRow({
  step,
  index,
  captureKeys,
  readOnly,
  onChange,
  onRemove,
}: {
  step: ConversationStep;
  index: number;
  captureKeys: string[];
  readOnly: boolean;
  onChange: (patch: Partial<ConversationStep>) => void;
  onRemove: () => void;
}) {
  const kind = stepKind(step);

  const setKind = (next: StepKind) => {
    if (next === "navigate") {
      onChange({ action: "send_keys", keys: step.keys ?? "", resultKey: undefined, value: undefined });
    } else if (next === "extract") {
      onChange({
        action: "save_value",
        resultKey: step.resultKey ?? captureKeys[0] ?? "",
        value: step.value ?? "",
        keys: undefined,
      });
    } else {
      onChange({ action: "hang_up", listenFor: step.listenFor, keys: undefined, resultKey: undefined, value: undefined });
    }
  };

  return (
    <tr className="editor-table-row">
      <td className="editor-table-num">{index + 1}</td>
      <td>
        <select
          className="editor-input editor-input-sm"
          value={kind}
          onChange={(e) => setKind(e.target.value as StepKind)}
          disabled={readOnly}
        >
          <option value="navigate">Navigate</option>
          <option value="extract">Extract</option>
          <option value="end">End</option>
        </select>
      </td>
      <td>
        <input
          className="editor-input"
          value={step.listenFor}
          onChange={(e) => onChange({ listenFor: e.target.value })}
          placeholder="IVR phrase"
          disabled={readOnly || kind === "end"}
        />
      </td>
      <td>
        {kind === "navigate" ? (
          <input
            className="editor-input mono"
            value={step.keys ?? ""}
            onChange={(e) => onChange({ keys: e.target.value })}
            placeholder="DTMF"
            disabled={readOnly}
          />
        ) : (
          <span className="editor-table-dash">—</span>
        )}
      </td>
      <td>
        {kind === "extract" ? (
          <select
            className="editor-input"
            value={step.resultKey ?? ""}
            onChange={(e) => onChange({ resultKey: e.target.value })}
            disabled={readOnly}
          >
            <option value="">Capture</option>
            {captureKeys.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        ) : (
          <span className="editor-table-dash">—</span>
        )}
      </td>
      <td>
        {kind === "extract" ? (
          <input
            className="editor-input"
            value={step.value ?? ""}
            onChange={(e) => onChange({ value: e.target.value })}
            placeholder="Status"
            disabled={readOnly}
          />
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
  const captureKeys = script.results.map((r) => r.key).filter(Boolean);

  const updateConversation = (conversation: ConversationStep[]) => onPatch({ conversation });

  const updateStep = (index: number, patch: Partial<ConversationStep>) => {
    updateConversation(script.conversation.map((s, i) => (i === index ? { ...s, ...patch } : s)));
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
        <h1 className="editor-title">{script.name || "Untitled"}</h1>
        {onTest && (
          <button type="button" className="btn btn-primary btn-sm" onClick={onTest}>
            Test
          </button>
        )}
      </header>

      <div className="editor-body">
        <section className="editor-section">
          <h2 className="editor-section-heading">Basics</h2>
          <p className="editor-section-desc">Name and target for this template.</p>
          <div className="editor-field-grid">
            <label className="editor-field">
              <span>Name</span>
              <input
                className="editor-input"
                value={script.name}
                onChange={(e) => onPatch({ name: e.target.value })}
                disabled={readOnly}
              />
            </label>
            <label className="editor-field">
              <span>Target</span>
              <input
                className="editor-input"
                type="tel"
                value={script.target}
                onChange={(e) => onPatch({ target: e.target.value })}
                disabled={readOnly}
              />
            </label>
            <label className="editor-field editor-field-wide">
              <span>Description</span>
              <input
                className="editor-input"
                value={script.description}
                onChange={(e) => onPatch({ description: e.target.value })}
                disabled={readOnly}
              />
            </label>
            <label className="editor-field">
              <span>Timeout (seconds)</span>
              <input
                className="editor-input"
                type="number"
                value={Math.round(script.timeoutMs / 1000)}
                onChange={(e) => onPatch({ timeoutMs: Number(e.target.value) * 1000 })}
                disabled={readOnly}
              />
            </label>
          </div>
        </section>

        <section className="editor-section">
          <h2 className="editor-section-heading">Secrets</h2>
          <p className="editor-section-desc">Values the runner provides at call time. Never stored in the template.</p>
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Example</th>
                  <th className="editor-table-col-check">Req</th>
                  <th className="editor-table-col-actions" />
                </tr>
              </thead>
              <tbody>
                {script.secrets.map((secret, i) => (
                  <tr key={secret.id} className="editor-table-row">
                    <td>
                      <input
                        className="editor-input mono"
                        value={secret.name}
                        onChange={(e) => {
                          const secrets = [...script.secrets];
                          secrets[i] = { ...secret, name: e.target.value };
                          onPatch({ secrets });
                        }}
                        disabled={readOnly}
                      />
                    </td>
                    <td>
                      <input
                        className="editor-input"
                        value={secret.description}
                        onChange={(e) => {
                          const secrets = [...script.secrets];
                          secrets[i] = { ...secret, description: e.target.value };
                          onPatch({ secrets });
                        }}
                        disabled={readOnly}
                      />
                    </td>
                    <td>
                      <input
                        className="editor-input"
                        value={secret.example}
                        onChange={(e) => {
                          const secrets = [...script.secrets];
                          secrets[i] = { ...secret, example: e.target.value };
                          onPatch({ secrets });
                        }}
                        disabled={readOnly}
                      />
                    </td>
                    <td className="editor-table-col-check">
                      <input
                        type="checkbox"
                        checked={secret.required}
                        onChange={(e) => {
                          const secrets = [...script.secrets];
                          secrets[i] = { ...secret, required: e.target.checked };
                          onPatch({ secrets });
                        }}
                        disabled={readOnly}
                      />
                    </td>
                    <td className="editor-table-actions">
                      {!readOnly && (
                        <button
                          type="button"
                          className="btn-icon"
                          onClick={() => onPatch({ secrets: script.secrets.filter((s) => s.id !== secret.id) })}
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
              onClick={() => onPatch({ secrets: [...script.secrets, newSecret()] })}
            >
              + Secret
            </button>
          )}
        </section>

        <section className="editor-section">
          <h2 className="editor-section-heading">Captures</h2>
          <p className="editor-section-desc">Fields you extract from the IVR. Flow steps reference these.</p>
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th>Capture</th>
                  <th>Description</th>
                  <th className="editor-table-col-actions" />
                </tr>
              </thead>
              <tbody>
                {script.results.map((result, i) => (
                  <tr key={result.id} className="editor-table-row">
                    <td>
                      <input
                        className="editor-input mono"
                        value={result.key}
                        onChange={(e) => {
                          const results = [...script.results];
                          results[i] = { ...result, key: e.target.value };
                          onPatch({ results });
                        }}
                        disabled={readOnly}
                        placeholder="balance"
                      />
                    </td>
                    <td>
                      <input
                        className="editor-input"
                        value={result.description}
                        onChange={(e) => {
                          const results = [...script.results];
                          results[i] = { ...result, description: e.target.value };
                          onPatch({ results });
                        }}
                        disabled={readOnly}
                      />
                    </td>
                    <td className="editor-table-actions">
                      {!readOnly && (
                        <button
                          type="button"
                          className="btn-icon"
                          onClick={() => onPatch({ results: script.results.filter((r) => r.id !== result.id) })}
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
              onClick={() => onPatch({ results: [...script.results, newResult()] })}
            >
              + Capture
            </button>
          )}
        </section>

        <section className="editor-section editor-section-wide">
          <h2 className="editor-section-heading">Flow</h2>
          <p className="editor-section-desc">
            <strong>Navigate</strong> — Listen + Send. <strong>Extract</strong> — Listen + Capture + Status.
          </p>
          <div className="editor-table-wrap">
            <table className="editor-table">
              <thead>
                <tr>
                  <th className="editor-table-col-num">#</th>
                  <th className="editor-table-col-type">Type</th>
                  <th>Listen</th>
                  <th>Send</th>
                  <th>Capture</th>
                  <th>Status</th>
                  <th className="editor-table-col-actions" />
                </tr>
              </thead>
              <tbody>
                {script.conversation.map((step, i) => (
                  <FlowRow
                    key={step.id}
                    step={step}
                    index={i}
                    captureKeys={captureKeys}
                    readOnly={readOnly}
                    onChange={(patch) => updateStep(i, patch)}
                    onRemove={() => updateConversation(script.conversation.filter((_, j) => j !== i))}
                  />
                ))}
              </tbody>
            </table>
          </div>
          {!readOnly && (
            <div className="editor-table-add-row">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => updateConversation([...script.conversation, newConversationStep("send_keys")])}
              >
                + Step
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
