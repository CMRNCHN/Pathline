import { useEffect, useMemo, useState } from "react";
import type { EditorSection } from "../script/types";
import { compileToRules } from "../script/compile";
import { newResult, newSecret } from "../script/compile";
import { useScripts } from "../context/ScriptContext";
import { ScriptsSidebar } from "./ScriptsSidebar";
import { ConversationEditor } from "./ConversationEditor";

interface ScriptEditorProps {
  onTest?: (scriptId: string) => void;
}

const SECTIONS: { id: EditorSection; label: string }[] = [
  { id: "basics", label: "Basics" },
  { id: "secrets", label: "Secrets" },
  { id: "conversation", label: "Conversation" },
  { id: "results", label: "Results" },
];

export function ScriptEditor({ onTest }: ScriptEditorProps) {
  const {
    activeScript,
    isActiveBundled,
    updateActive,
    removeCustom,
    duplicateToCustom,
    importScript,
  } = useScripts();

  const [section, setSection] = useState<EditorSection>("conversation");

  useEffect(() => {
    if (activeScript && !activeScript.setupComplete) setSection("basics");
  }, [activeScript?.id, activeScript?.setupComplete]);

  const jsonPreview = useMemo(() => {
    if (!activeScript) return "{}";
    return JSON.stringify(activeScript, null, 2);
  }, [activeScript]);

  if (!activeScript) {
    return (
      <div className="script-workspace">
        <ScriptsSidebar onImport={importScript} />
        <div className="script-editor-empty">
          <p className="hint">No scripts yet.</p>
        </div>
      </div>
    );
  }

  const readOnly = isActiveBundled;
  const showBasicsSection = section === "basics" || !activeScript.setupComplete;

  const exportJson = () => {
    const blob = new Blob([JSON.stringify(activeScript, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeScript.name.replace(/\s+/g, "-").toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const finishBasics = () => {
    updateActive({ setupComplete: true });
    setSection("secrets");
  };

  return (
    <div className="script-workspace">
      <ScriptsSidebar onImport={importScript} />

      <div className="script-editor-panel">
        {readOnly && (
          <div className="bundled-banner">
            Example script (read-only).{" "}
            <button className="btn btn-sm btn-secondary" onClick={() => duplicateToCustom(activeScript)}>
              Duplicate to edit
            </button>
          </div>
        )}

        <header className="editor-topbar">
          <h1 className="editor-title">{activeScript.name || "Untitled script"}</h1>
          <div className="editor-topbar-actions">
            {onTest && (
              <button className="btn btn-primary btn-sm" onClick={() => onTest(activeScript.id)}>
                Test
              </button>
            )}
            <button className="btn btn-secondary btn-sm" onClick={() => duplicateToCustom(activeScript)}>
              Duplicate
            </button>
            <button className="btn btn-secondary btn-sm" onClick={exportJson}>Export</button>
            {!readOnly && (
              <button className="btn btn-danger btn-sm" onClick={() => removeCustom(activeScript.id)}>
                Delete
              </button>
            )}
          </div>
        </header>

        <nav className="section-nav">
          {SECTIONS.map((s) => {
            if (s.id === "basics" && activeScript.setupComplete && section !== "basics") {
              return null;
            }
            return (
              <button
                key={s.id}
                className={`section-tab ${section === s.id ? "active" : ""}`}
                onClick={() => setSection(s.id)}
              >
                {s.label}
              </button>
            );
          })}
          {activeScript.setupComplete && section !== "basics" && (
            <button className="section-tab section-tab-muted" onClick={() => setSection("basics")}>
              Basics
            </button>
          )}
        </nav>

        <div className="editor-scroll">
          {showBasicsSection && (
            <section className="editor-section">
              <header className="section-header">
                <h2>Basics</h2>
                <p className="hint">What is this check? You can hide this after setup.</p>
              </header>
              <div className="basics-grid">
                <div className="form-group">
                  <label>Name</label>
                  <input
                    value={activeScript.name}
                    onChange={(e) => updateActive({ name: e.target.value })}
                    placeholder="Credit Card Balance Check"
                    disabled={readOnly}
                  />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <input
                    value={activeScript.description}
                    onChange={(e) => updateActive({ description: e.target.value })}
                    placeholder="Check if my card is current"
                    disabled={readOnly}
                  />
                </div>
                <div className="form-group">
                  <label>Target number</label>
                  <input
                    type="tel"
                    value={activeScript.target}
                    onChange={(e) => updateActive({ target: e.target.value })}
                    placeholder="+18001234567"
                    disabled={readOnly}
                  />
                </div>
                <div className="form-group">
                  <label>Timeout (seconds)</label>
                  <input
                    type="number"
                    value={Math.round(activeScript.timeoutMs / 1000)}
                    onChange={(e) => updateActive({ timeoutMs: Number(e.target.value) * 1000 })}
                    disabled={readOnly}
                  />
                </div>
                <div className="form-group form-group-full">
                  <label>Tags</label>
                  <input
                    value={activeScript.tags.join(", ")}
                    onChange={(e) =>
                      updateActive({
                        tags: e.target.value.split(",").map((t) => t.trim()).filter(Boolean),
                      })
                    }
                    placeholder="Credit Card, Bank"
                    disabled={readOnly}
                  />
                </div>
              </div>
              {!readOnly && (
                <button className="btn btn-primary" onClick={finishBasics}>
                  Done — continue to secrets
                </button>
              )}
            </section>
          )}

          {section === "secrets" && (
            <section className="editor-section">
              <header className="section-header">
                <h2>Required secrets</h2>
                <p className="hint">What this script needs at run time — card number, PIN, zip, etc.</p>
              </header>
              {activeScript.secrets.map((secret, i) => (
                <div key={secret.id} className="secret-row">
                  <div className="form-group">
                    <label>Name</label>
                    <input
                      className="mono"
                      value={secret.name}
                      onChange={(e) => {
                        const secrets = [...activeScript.secrets];
                        secrets[i] = { ...secret, name: e.target.value };
                        updateActive({ secrets });
                      }}
                      placeholder="cc_num"
                      disabled={readOnly}
                    />
                  </div>
                  <div className="form-group">
                    <label>Description</label>
                    <input
                      value={secret.description}
                      onChange={(e) => {
                        const secrets = [...activeScript.secrets];
                        secrets[i] = { ...secret, description: e.target.value };
                        updateActive({ secrets });
                      }}
                      placeholder="Full card number"
                      disabled={readOnly}
                    />
                  </div>
                  <div className="form-group">
                    <label>Example</label>
                    <input
                      value={secret.example}
                      onChange={(e) => {
                        const secrets = [...activeScript.secrets];
                        secrets[i] = { ...secret, example: e.target.value };
                        updateActive({ secrets });
                      }}
                      placeholder="4111…"
                      disabled={readOnly}
                    />
                  </div>
                  <label className="required-check">
                    <input
                      type="checkbox"
                      checked={secret.required}
                      onChange={(e) => {
                        const secrets = [...activeScript.secrets];
                        secrets[i] = { ...secret, required: e.target.checked };
                        updateActive({ secrets });
                      }}
                      disabled={readOnly}
                    />
                    Required
                  </label>
                  {!readOnly && (
                    <button
                      className="btn-icon"
                      onClick={() =>
                        updateActive({ secrets: activeScript.secrets.filter((s) => s.id !== secret.id) })
                      }
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
              {!readOnly && (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => updateActive({ secrets: [...activeScript.secrets, newSecret()] })}
                >
                  + Add secret
                </button>
              )}
            </section>
          )}

          {section === "conversation" && (
            <ConversationEditor
              script={activeScript}
              readOnly={readOnly}
              onChange={(conversation) => updateActive({ conversation })}
            />
          )}

          {section === "results" && (
            <section className="editor-section">
              <header className="section-header">
                <h2>Captured values</h2>
                <p className="hint">Define the fields your script saves. Conversation steps reference these.</p>
              </header>
              {activeScript.results.map((result, i) => (
                <div key={result.id} className="result-row">
                  <div className="form-group">
                    <label>JSON key</label>
                    <input
                      className="mono"
                      value={result.key}
                      onChange={(e) => {
                        const results = [...activeScript.results];
                        results[i] = { ...result, key: e.target.value };
                        updateActive({ results });
                      }}
                      placeholder="balance_status"
                      disabled={readOnly}
                    />
                  </div>
                  <div className="form-group">
                    <label>Description</label>
                    <input
                      value={result.description}
                      onChange={(e) => {
                        const results = [...activeScript.results];
                        results[i] = { ...result, description: e.target.value };
                        updateActive({ results });
                      }}
                      placeholder="Whether the account is current"
                      disabled={readOnly}
                    />
                  </div>
                  {!readOnly && (
                    <button
                      className="btn-icon"
                      onClick={() =>
                        updateActive({ results: activeScript.results.filter((r) => r.id !== result.id) })
                      }
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
              {!readOnly && (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => updateActive({ results: [...activeScript.results, newResult()] })}
                >
                  + Add captured value
                </button>
              )}
            </section>
          )}
        </div>

        <footer className="json-dock">
          <div className="json-dock-header">
            <span>JSON</span>
            <span className="hint">{compileToRules(activeScript).length} compiled rules</span>
          </div>
          <pre className="json-dock-body">{jsonPreview}</pre>
        </footer>
      </div>
    </div>
  );
}
