import type { ConversationStep, ScriptAction, ScriptDocument } from "../script/types";
import { ACTION_LABELS } from "../script/types";
import { actionLabel, newConversationStep } from "../script/compile";

const ACTIONS: ScriptAction[] = [
  "send_keys",
  "save_value",
  "speak",
  "wait",
  "hang_up",
  "jump",
];

interface ConversationEditorProps {
  script: ScriptDocument;
  readOnly: boolean;
  onChange: (conversation: ConversationStep[]) => void;
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

export function ConversationEditor({ script, readOnly, onChange }: ConversationEditorProps) {
  const resultKeys = script.results.map((r) => r.key).filter(Boolean);
  const stepIds = script.conversation.map((s, i) => ({
    id: s.id,
    label: `${i + 1}. ${actionLabel(s.action)}`,
  }));

  const updateStep = (index: number, patch: Partial<ConversationStep>) => {
    onChange(script.conversation.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  };

  const removeStep = (index: number) => {
    onChange(script.conversation.filter((_, i) => i !== index));
  };

  const addStep = (action: ScriptAction = "send_keys") => {
    onChange([...script.conversation, newConversationStep(action)]);
  };

  return (
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
  );
}
