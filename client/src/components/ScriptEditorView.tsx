import { useState } from "react";
import type {
  ConversationStep,
  EditorSection,
  ScriptAction,
  ScriptDocument,
} from "../script/types";
import { ACTION_LABELS } from "../script/types";
import {
  actionLabel,
  newConversationStep,
  newResult,
  newSecret,
} from "../script/compile";
import {
  initialSectionForScript,
  nextSectionAfterBasics,
  shouldShowBasicsSection,
} from "../script/setupFlow";

const SECTIONS: { id: EditorSection; label: string }[] = [
  { id: "basics", label: "Basics" },
  { id: "secrets", label: "Secrets" },
  { id: "conversation", label: "Conversation" },
  { id: "results", label: "Results" },
];

const ACTIONS: ScriptAction[] = ["send_keys", "save_value", "speak", "wait", "hang_up", "jump"];

function exportScriptJson(script: ScriptDocument): void {
  const blob = new Blob([JSON.stringify(script, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const slug = script.name.replace(/\s+/g, "-").toLowerCase() || "script";
  a.download = `${slug}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function TimelineRow({
  step,
  index,
  resultKeys,
  stepIds,
  readOnly,
  onChange,
  onRemove,
}: {
  step: ConversationStep;
  index: number;
  resultKeys: string[];
  stepIds: { id: string; label: string }[];
  readOnly: boolean;
  onChange: (patch: Partial<ConversationStep>) => void;
  onRemove: () => void;
}) {
  const needsListen =
    step.action === "send_keys" ||
    step.action === "save_value" ||
    (step.action === "hang_up" && !step.listenFor);

  return (
    <div className="timeline-row">
      <div className="timeline-index">{index + 1}</div>
      <div className="timeline-body">
        {needsListen && step.action !== "hang_up" && (
          <div className="timeline-field">
            <span className="timeline-label">When I hear</span>
            <input
              value={step.listenFor}
              onChange={(e) => onChange({ listenFor: e.target.value })}
              placeholder=""
              disabled={readOnly}
            />
          </div>
        )}

        {step.action === "hang_up" && (
          <div className="timeline-field">
            <span className="timeline-label">When I hear</span>
            <input
              value={step.listenFor}
              onChange={(e) => onChange({ listenFor: e.target.value })}
              placeholder=""
              disabled={readOnly}
            />
          </div>
        )}

        <div className="timeline-arrow">↓</div>

        <div className="timeline-field">
          <span className="timeline-label">Then</span>
          <select
            value={step.action}
            onChange={(e) => {
              const action = e.target.value as ScriptAction;
              onChange({
                action,
                keys: action === "send_keys" ? step.keys ?? "" : undefined,
                resultKey: action === "save_value" ? step.resultKey ?? resultKeys[0] : undefined,
                value: action === "save_value" ? step.value ?? "" : undefined,
                speakText: action === "speak" ? step.speakText ?? "" : undefined,
                waitMs: action === "wait" ? step.waitMs ?? 1000 : undefined,
                jumpToStepId: action === "jump" ? step.jumpToStepId : undefined,
              });
            }}
            disabled={readOnly}
          >
            {ACTIONS.map((a) => (
              <option key={a} value={a}>{ACTION_LABELS[a]}</option>
            ))}
          </select>
        </div>

        {step.action === "send_keys" && (
          <div className="timeline-field">
            <span className="timeline-label">Keys to send</span>
            <input
              className="mono"
              value={step.keys ?? ""}
              onChange={(e) => onChange({ keys: e.target.value })}
              placeholder=""
              disabled={readOnly}
            />
          </div>
        )}

        {step.action === "save_value" && (
          <>
            <div className="timeline-field">
              <span className="timeline-label">Save as</span>
              <select
                value={step.resultKey ?? ""}
                onChange={(e) => onChange({ resultKey: e.target.value })}
                disabled={readOnly}
              >
                <option value="">Pick a result…</option>
                {resultKeys.map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </div>
            <div className="timeline-field">
              <span className="timeline-label">Value</span>
              <input
                value={step.value ?? ""}
                onChange={(e) => onChange({ value: e.target.value })}
                placeholder=""
                disabled={readOnly}
              />
            </div>
          </>
        )}

        {step.action === "speak" && (
          <div className="timeline-field">
            <span className="timeline-label">Say</span>
            <input
              value={step.speakText ?? ""}
              onChange={(e) => onChange({ speakText: e.target.value })}
              placeholder=""
              disabled={readOnly}
            />
          </div>
        )}

        {step.action === "wait" && (
          <div className="timeline-field">
            <span className="timeline-label">Milliseconds</span>
            <input
              type="number"
              value={step.waitMs ?? 1000}
              onChange={(e) => onChange({ waitMs: Number(e.target.value) })}
              disabled={readOnly}
            />
          </div>
        )}

        {step.action === "jump" && (
          <div className="timeline-field">
            <span className="timeline-label">Jump to step</span>
            <select
              value={step.jumpToStepId ?? ""}
              onChange={(e) => onChange({ jumpToStepId: e.target.value })}
              disabled={readOnly}
            >
              <option value="">Select…</option>
              {stepIds.filter((s) => s.id !== step.id).map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </div>
        )}

        {step.action === "hang_up" && !step.listenFor && (
          <p className="timeline-end-label">End call</p>
        )}
      </div>

      {!readOnly && (
        <button className="btn-icon timeline-remove" onClick={onRemove} title="Remove">×</button>
      )}
    </div>
  );
}

export interface ScriptEditorViewProps {
  script: ScriptDocument;
  readOnly: boolean;
  onPatch: (patch: Partial<ScriptDocument>) => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onTest?: () => void;
}

export function ScriptEditorView({
  script,
  readOnly,
  onPatch,
  onDuplicate,
  onDelete,
  onTest,
}: ScriptEditorViewProps) {
  const [section, setSection] = useState<EditorSection>(() =>
    initialSectionForScript(script.setupComplete)
  );

  const showBasicsSection = shouldShowBasicsSection(section, script.setupComplete);
  const resultKeys = script.results.map((r) => r.key).filter(Boolean);
  const stepIds = script.conversation.map((s, i) => ({
    id: s.id,
    label: `${i + 1}. ${actionLabel(s.action)}`,
  }));

  const updateConversation = (conversation: ConversationStep[]) => onPatch({ conversation });

  const updateStep = (index: number, patch: Partial<ConversationStep>) => {
    updateConversation(script.conversation.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const removeStep = (index: number) => {
    updateConversation(script.conversation.filter((_, i) => i !== index));
  };

  const addStep = (action: ScriptAction = "send_keys") => {
    updateConversation([...script.conversation, newConversationStep(action)]);
  };

  const handleFinishBasics = () => {
    onPatch({ setupComplete: true });
    setSection(nextSectionAfterBasics());
  };

  return (
    <div className="script-editor-panel">
      {readOnly && (
        <div className="bundled-banner">
          Example script (read-only).{" "}
          <button className="btn btn-sm btn-secondary" onClick={onDuplicate}>
            Duplicate to edit
          </button>
        </div>
      )}

      <header className="editor-topbar">
        <h1 className="editor-title">{script.name || "Untitled script"}</h1>
        <div className="editor-topbar-actions">
          {onTest && (
            <button className="btn btn-primary btn-sm" onClick={onTest}>
              Test
            </button>
          )}
          <button className="btn btn-secondary btn-sm" onClick={onDuplicate}>
            Duplicate
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => exportScriptJson(script)}>
            Export
          </button>
          {!readOnly && (
            <button className="btn btn-danger btn-sm" onClick={onDelete}>
              Delete
            </button>
          )}
        </div>
      </header>

      <nav className="section-nav">
        {SECTIONS.map((s) => {
          if (s.id === "basics" && script.setupComplete && section !== "basics") {
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
        {script.setupComplete && section !== "basics" && (
          <button
            className="section-tab section-tab-muted"
            onClick={() => setSection("basics")}
          >
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
                  value={script.name}
                  onChange={(e) => onPatch({ name: e.target.value })}
                  disabled={readOnly}
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input
                  value={script.description}
                  onChange={(e) => onPatch({ description: e.target.value })}
                  disabled={readOnly}
                />
              </div>
              <div className="form-group">
                <label>Target number</label>
                <input
                  type="tel"
                  value={script.target}
                  onChange={(e) => onPatch({ target: e.target.value })}
                  disabled={readOnly}
                />
              </div>
              <div className="form-group">
                <label>Timeout (seconds)</label>
                <input
                  type="number"
                  value={Math.round(script.timeoutMs / 1000)}
                  onChange={(e) => onPatch({ timeoutMs: Number(e.target.value) * 1000 })}
                  disabled={readOnly}
                />
              </div>
              <div className="form-group form-group-full">
                <label>Tags</label>
                <input
                  value={script.tags.join(", ")}
                  onChange={(e) =>
                    onPatch({
                      tags: e.target.value.split(",").map((t) => t.trim()).filter(Boolean),
                    })
                  }
                  disabled={readOnly}
                />
              </div>
            </div>
            {!readOnly && (
              <button className="btn btn-primary" onClick={handleFinishBasics}>
                Done — continue to secrets
              </button>
            )}
          </section>
        )}

        {section === "secrets" && (
          <section className="editor-section">
            <header className="section-header">
              <h2>Required secrets</h2>
              <p className="hint">Values this script needs when you run it.</p>
            </header>
            {script.secrets.map((secret, i) => (
              <div key={secret.id} className="secret-row">
                <div className="form-group">
                  <label>Name</label>
                  <input
                    className="mono"
                    value={secret.name}
                    onChange={(e) => {
                      const secrets = [...script.secrets];
                      secrets[i] = { ...secret, name: e.target.value };
                      onPatch({ secrets });
                    }}
                    disabled={readOnly}
                  />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <input
                    value={secret.description}
                    onChange={(e) => {
                      const secrets = [...script.secrets];
                      secrets[i] = { ...secret, description: e.target.value };
                      onPatch({ secrets });
                    }}
                    disabled={readOnly}
                  />
                </div>
                <div className="form-group">
                  <label>Example</label>
                  <input
                    value={secret.example}
                    onChange={(e) => {
                      const secrets = [...script.secrets];
                      secrets[i] = { ...secret, example: e.target.value };
                      onPatch({ secrets });
                    }}
                    disabled={readOnly}
                  />
                </div>
                <label className="required-check">
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
                  Required
                </label>
                {!readOnly && (
                  <button
                    className="btn-icon"
                    onClick={() => onPatch({ secrets: script.secrets.filter((s) => s.id !== secret.id) })}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            {!readOnly && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => onPatch({ secrets: [...script.secrets, newSecret()] })}
              >
                + Add secret
              </button>
            )}
          </section>
        )}

        {section === "conversation" && (
          <section className="editor-section">
            <header className="section-header">
              <h2>Conversation</h2>
              <p className="hint">Each step is <strong>when I hear</strong> → <strong>then</strong>.</p>
            </header>

            <div className="timeline">
              {script.conversation.map((step, i) => (
                <TimelineRow
                  key={step.id}
                  step={step}
                  index={i}
                  resultKeys={resultKeys}
                  stepIds={stepIds}
                  readOnly={readOnly}
                  onChange={(patch) => updateStep(i, patch)}
                  onRemove={() => removeStep(i)}
                />
              ))}
            </div>

            {!readOnly && (
              <div className="timeline-add">
                <button className="btn btn-secondary btn-sm" onClick={() => addStep("send_keys")}>
                  + Step
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => addStep("save_value")}>
                  + Save result
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => addStep("hang_up")}>
                  + End call
                </button>
              </div>
            )}
          </section>
        )}

        {section === "results" && (
          <section className="editor-section">
            <header className="section-header">
              <h2>Captured values</h2>
              <p className="hint">Define the fields your script saves. Conversation steps reference these.</p>
            </header>
            {script.results.map((result, i) => (
              <div key={result.id} className="result-row">
                <div className="form-group">
                  <label>Field name</label>
                  <input
                    className="mono"
                    value={result.key}
                    onChange={(e) => {
                      const results = [...script.results];
                      results[i] = { ...result, key: e.target.value };
                      onPatch({ results });
                    }}
                    disabled={readOnly}
                  />
                </div>
                <div className="form-group">
                  <label>Description</label>
                  <input
                    value={result.description}
                    onChange={(e) => {
                      const results = [...script.results];
                      results[i] = { ...result, description: e.target.value };
                      onPatch({ results });
                    }}
                    disabled={readOnly}
                  />
                </div>
                {!readOnly && (
                  <button
                    className="btn-icon"
                    onClick={() => onPatch({ results: script.results.filter((r) => r.id !== result.id) })}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            {!readOnly && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => onPatch({ results: [...script.results, newResult()] })}
              >
                + Add captured value
              </button>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
