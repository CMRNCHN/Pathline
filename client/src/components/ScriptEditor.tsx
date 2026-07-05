import { useRef, useState } from "react";
import type { StatusRule } from "../script/types";
import { isSendRule, newCaptureRule, newSendRule } from "../script/storage";
import { useScripts } from "../context/ScriptContext";

function RuleCard({
  rule,
  index,
  readOnly,
  onChange,
  onRemove,
}: {
  rule: StatusRule;
  index: number;
  readOnly: boolean;
  onChange: (patch: Partial<StatusRule>) => void;
  onRemove: () => void;
}) {
  const send = isSendRule(rule);

  const setKind = (kind: "send" | "capture") => {
    if (kind === "send") {
      onChange({ response: "", key: "", status: "", endCall: false });
    } else {
      onChange({ trigger: "", dtmf: "", endCall: true });
    }
  };

  return (
    <div className={`outcome-card outcome-${send ? "send" : "capture"}`}>
      <div className="outcome-card-top">
        <span className="step-num-badge">{index + 1}</span>
        <div className="branch-type-toggle">
          <button
            type="button"
            className={`branch-type-btn ${send ? "active" : ""}`}
            onClick={() => !readOnly && setKind("send")}
            disabled={readOnly}
          >
            Send DTMF
          </button>
          <button
            type="button"
            className={`branch-type-btn ${!send ? "active" : ""}`}
            onClick={() => !readOnly && setKind("capture")}
            disabled={readOnly}
          >
            Capture status
          </button>
        </div>
        {!readOnly && (
          <button className="btn-icon" onClick={onRemove} title="Remove rule">×</button>
        )}
      </div>

      {send ? (
        <div className="outcome-fields">
          <div className="outcome-field-row">
            <label>When I hear (trigger)</label>
            <input
              value={rule.trigger ?? ""}
              onChange={(e) => onChange({ trigger: e.target.value })}
              placeholder="monitored or recorded|zip code"
              disabled={readOnly}
            />
          </div>
          <div className="outcome-field-row">
            <label>I send (DTMF)</label>
            <input
              className="mono"
              value={rule.dtmf ?? ""}
              onChange={(e) => onChange({ dtmf: e.target.value })}
              placeholder="**11  or  {account_pin}#"
              disabled={readOnly}
            />
          </div>
        </div>
      ) : (
        <div className="outcome-fields">
          <div className="outcome-field-row">
            <label>When I hear (response)</label>
            <input
              value={rule.response}
              onChange={(e) => onChange({ response: e.target.value })}
              placeholder="account is current|payment due"
              disabled={readOnly}
            />
          </div>
          <div className="outcome-field-row">
            <label>JSON key</label>
            <input
              className="mono"
              value={rule.key}
              onChange={(e) => onChange({ key: e.target.value })}
              placeholder="account_status"
              disabled={readOnly}
            />
          </div>
          <div className="outcome-field-row">
            <label>Means (status value)</label>
            <input
              value={rule.status}
              onChange={(e) => onChange({ status: e.target.value })}
              placeholder="current"
              disabled={readOnly}
            />
          </div>
        </div>
      )}

      <div className="outcome-footer">
        <label className="end-call-label">
          <input
            type="checkbox"
            checked={Boolean(rule.endCall)}
            onChange={(e) => onChange({ endCall: e.target.checked })}
            disabled={readOnly}
          />
          End call & submit status
        </label>
      </div>
    </div>
  );
}

export function ScriptEditor() {
  const {
    scripts,
    bundledIds,
    activeScript,
    activeId,
    setActiveId,
    isActiveBundled,
    updateActive,
    addCustom,
    removeCustom,
    duplicateToCustom,
    importScript,
    updateActiveRule,
    addActiveRule,
    removeActiveRule,
    addSecretKey,
    removeSecretKey,
    syncActiveSecrets,
  } = useScripts();

  const [newSecret, setNewSecret] = useState("");
  const [showJson, setShowJson] = useState(false);
  const importRef = useRef<HTMLInputElement>(null);

  if (!activeScript) {
    return (
      <div className="script-editor-empty">
        <p className="hint">No scripts yet.</p>
        <button className="btn btn-primary" onClick={() => addCustom()}>Create script</button>
      </div>
    );
  }

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(activeScript, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeScript.name.replace(/\s+/g, "-").toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = async (file: File) => {
    try {
      const text = await file.text();
      importScript(JSON.parse(text));
    } catch {
      alert("Invalid script JSON");
    }
  };

  return (
    <div className="template-builder">
      <aside className="template-sidebar">
        <section>
          <div className="sidebar-head">
            <h3>Scripts</h3>
            <button className="btn btn-sm btn-secondary" onClick={() => addCustom()}>+</button>
          </div>
          <ul className="sidebar-list">
            {scripts.map((s) => (
              <li key={s.id}>
                <button
                  className={`sidebar-item ${s.id === activeId ? "active" : ""}`}
                  onClick={() => setActiveId(s.id)}
                >
                  {bundledIds.has(s.id) ? "📦 " : ""}{s.name}
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="secrets-section-panel">
          <div className="sidebar-head">
            <h3>Local secrets</h3>
            {!isActiveBundled && (
              <button className="btn btn-sm btn-secondary" onClick={syncActiveSecrets} title="Detect {keys} from DTMF">
                ↻
              </button>
            )}
          </div>
          <p className="field-hint">Used at call time — never sent to server</p>
          {(activeScript.secrets ?? []).map((key) => (
            <div key={key} className="secret-field">
              <div className="secret-field-row">
                <label>{key}</label>
                {!isActiveBundled && (
                  <button className="btn-icon" onClick={() => removeSecretKey(key)}>×</button>
                )}
              </div>
              <input disabled placeholder="Set value on Call tab" />
            </div>
          ))}
          {!isActiveBundled && (
            <div className="add-secret-row">
              <input
                className="mono"
                value={newSecret}
                onChange={(e) => setNewSecret(e.target.value)}
                placeholder="account_pin"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    addSecretKey(newSecret);
                    setNewSecret("");
                  }
                }}
              />
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => {
                  addSecretKey(newSecret);
                  setNewSecret("");
                }}
              >
                Add
              </button>
            </div>
          )}
        </section>
      </aside>

      <div className="template-main">
        {isActiveBundled && (
          <div className="bundled-banner">
            Example script (read-only).{" "}
            <button className="btn btn-sm btn-secondary" onClick={() => duplicateToCustom(activeScript)}>
              Duplicate to edit
            </button>
          </div>
        )}

        <div className="template-main-header">
          <input
            className="template-name-input"
            value={activeScript.name}
            onChange={(e) => updateActive({ name: e.target.value })}
            disabled={isActiveBundled}
          />
          <div className="template-actions">
            {!isActiveBundled && (
              <button className="btn btn-danger btn-sm" onClick={() => removeCustom(activeScript.id)}>
                Delete
              </button>
            )}
            <button className="btn btn-secondary" onClick={() => setShowJson(!showJson)}>
              {showJson ? "Hide JSON" : "Preview JSON"}
            </button>
            <button className="btn btn-secondary" onClick={exportJson}>Export</button>
            <button className="btn btn-secondary" onClick={() => importRef.current?.click()}>
              Import
            </button>
            <input
              ref={importRef}
              type="file"
              accept="application/json"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleImport(file);
                e.target.value = "";
              }}
            />
          </div>
        </div>

        <input
          className="profile-name-input script-meta-input"
          value={activeScript.description ?? ""}
          onChange={(e) => updateActive({ description: e.target.value })}
          placeholder="Description"
          disabled={isActiveBundled}
        />

        <div className="form-group script-target-row">
          <label htmlFor="script-target">Default target number (optional)</label>
          <input
            id="script-target"
            type="tel"
            value={activeScript.target ?? ""}
            onChange={(e) => updateActive({ target: e.target.value })}
            placeholder="+15551234567"
            disabled={isActiveBundled}
          />
        </div>

        <p className="template-intro">
          <strong>Send DTMF</strong> — trigger phrase → touch-tone (use <code>{"{secret_key}"}</code> placeholders).
          <strong> Capture status</strong> — IVR response → <code>key: status</code> in collected JSON.
        </p>

        {activeScript.rules.map((rule, i) => (
          <RuleCard
            key={i}
            rule={rule}
            index={i}
            readOnly={isActiveBundled}
            onChange={(patch) => updateActiveRule(i, patch)}
            onRemove={() => removeActiveRule(i)}
          />
        ))}

        {!isActiveBundled && (
          <div className="add-outcome-btns">
            <button className="btn btn-secondary btn-sm" onClick={() => addActiveRule(newSendRule())}>
              + Send DTMF rule
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => addActiveRule(newCaptureRule())}>
              + Capture status rule
            </button>
          </div>
        )}

        {showJson && (
          <pre className="json-preview">{JSON.stringify(activeScript, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}
