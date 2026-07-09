import { useMemo, useState } from "react";
import type { IvrRule } from "../../script/types";
import {
  buildRuleFromDraft,
  draftSummary,
  type CaptureWizardDraft,
  type NavigateWizardDraft,
  type RespondWizardDraft,
  type RuleWizardType,
  ruleToDraft,
  validateDraft,
  type WizardDraft,
} from "../../script/ruleIntent";
import {
  CAPTURE_PRESETS,
  CUSTOM_PRESET_ID,
  findCapturePreset,
  findRespondPreset,
  NAVIGATE_KEYS,
  NAVIGATE_TRIGGER_PRESETS,
  RESPOND_PRESETS,
} from "../../script/rulePresets";

const INTENTS: { value: RuleWizardType; label: string; hint: string }[] = [
  { value: "capture", label: "Collect information from the IVR", hint: "Save something the IVR says aloud" },
  { value: "navigate", label: "Navigate through the IVR", hint: "Press keys, speak, or wait for menus" },
  { value: "respond", label: "Provide information to the IVR", hint: "Send account details when asked" },
  { value: "end", label: "End the call", hint: "Finish when this step runs" },
];

type WizardStep =
  | "intent"
  | "capture-info"
  | "capture-trigger"
  | "capture-save"
  | "navigate-mode"
  | "navigate-action"
  | "navigate-trigger"
  | "respond-info"
  | "respond-delivery"
  | "respond-variable"
  | "respond-trigger"
  | "summary";

interface RuleWizardProps {
  runtimeVariables: string[];
  existingLabels: string[];
  editingRule?: IvrRule;
  onAddVariable: (name: string) => void;
  onSave: (rule: IvrRule) => void;
  onCancel: () => void;
}

function stepLabel(step: WizardStep, wizardType: RuleWizardType | null): string {
  if (step === "intent") return "What should this step do?";
  if (step === "summary") return "Generated rule";

  switch (wizardType) {
    case "capture":
      if (step === "capture-info") return "What information are you collecting?";
      if (step === "capture-trigger") return "How do you know the IVR is providing this?";
      if (step === "capture-save") return "Should we save this value?";
      break;
    case "navigate":
      if (step === "navigate-mode") return "How should we navigate?";
      if (step === "navigate-action") return "What should the assistant do?";
      if (step === "navigate-trigger") return "What tells us to perform this action?";
      break;
    case "respond":
      if (step === "respond-info") return "What information does the IVR need?";
      if (step === "respond-delivery") return "How should it be provided?";
      if (step === "respond-variable") return "Which value should it use?";
      if (step === "respond-trigger") return "What tells us the IVR is asking?";
      break;
    case "end":
      break;
  }
  return "";
}

function stepProgress(step: WizardStep, wizardType: RuleWizardType | null): { current: number; total: number } {
  if (step === "intent") return { current: 1, total: 1 };
  if (step === "summary") {
    const totals: Record<RuleWizardType, number> = {
      capture: 5,
      navigate: 5,
      respond: 6,
      end: 2,
    };
    return { current: wizardType ? totals[wizardType] : 1, total: wizardType ? totals[wizardType] : 1 };
  }

  const captureSteps: WizardStep[] = ["capture-info", "capture-trigger", "capture-save", "summary"];
  const navigateSteps: WizardStep[] = ["navigate-mode", "navigate-action", "navigate-trigger", "summary"];
  const respondSteps: WizardStep[] = [
    "respond-info",
    "respond-delivery",
    "respond-variable",
    "respond-trigger",
    "summary",
  ];

  if (wizardType === "capture") {
    const idx = captureSteps.indexOf(step);
    return { current: idx + 2, total: 5 };
  }
  if (wizardType === "navigate") {
    if (step === "navigate-action") return { current: 3, total: 5 };
    const idx = navigateSteps.indexOf(step);
    return { current: idx + 2, total: 5 };
  }
  if (wizardType === "respond") {
    const idx = respondSteps.indexOf(step);
    return { current: idx + 2, total: 6 };
  }
  return { current: 1, total: 1 };
}

function firstStepForType(type: RuleWizardType): WizardStep {
  switch (type) {
    case "capture":
      return "capture-info";
    case "navigate":
      return "navigate-mode";
    case "respond":
      return "respond-info";
    case "end":
      return "summary";
  }
}

function initFromDraft(draft: WizardDraft | null): {
  wizardType: RuleWizardType | null;
  step: WizardStep;
  captureInfoPresetId: string;
  captureCustomOutput: string;
  captureTrigger: string;
  captureSave: boolean;
  captureOutput: string;
  navigateMode: NavigateWizardDraft["mode"];
  navigateLiteral: string;
  navigateTrigger: string;
  navigateWaitSeconds: number;
  respondInfoPresetId: string;
  respondCustomVariable: string;
  respondDelivery: RespondWizardDraft["delivery"];
  respondVariable: string;
  respondTrigger: string;
} {
  if (!draft) {
    return {
      wizardType: null,
      step: "intent",
      captureInfoPresetId: "",
      captureCustomOutput: "",
      captureTrigger: "",
      captureSave: true,
      captureOutput: "",
      navigateMode: "keypad",
      navigateLiteral: "1",
      navigateTrigger: "",
      navigateWaitSeconds: 3,
      respondInfoPresetId: "",
      respondCustomVariable: "",
      respondDelivery: "keypad",
      respondVariable: "",
      respondTrigger: "",
    };
  }

  const base = {
    wizardType: draft.intent,
    step: firstStepForType(draft.intent) as WizardStep,
    captureInfoPresetId: "",
    captureCustomOutput: "",
    captureTrigger: "",
    captureSave: true,
    captureOutput: "",
    navigateMode: "keypad" as NavigateWizardDraft["mode"],
    navigateLiteral: "1",
    navigateTrigger: "",
    navigateWaitSeconds: 3,
    respondInfoPresetId: "",
    respondCustomVariable: "",
    respondDelivery: "keypad" as RespondWizardDraft["delivery"],
    respondVariable: "",
    respondTrigger: "",
  };

  if (draft.intent === "capture") {
    const preset = CAPTURE_PRESETS.find((p) => p.outputVar === draft.output);
    return {
      ...base,
      step: "capture-info",
      captureInfoPresetId: preset?.id ?? CUSTOM_PRESET_ID,
      captureCustomOutput: draft.output,
      captureTrigger: draft.trigger,
      captureSave: draft.save,
      captureOutput: draft.output,
    };
  }
  if (draft.intent === "navigate") {
    return {
      ...base,
      step: "navigate-mode",
      navigateMode: draft.mode,
      navigateLiteral: draft.responseLiteral,
      navigateTrigger: draft.trigger,
      navigateWaitSeconds: draft.waitSeconds ?? 3,
    };
  }
  if (draft.intent === "respond") {
    const preset = RESPOND_PRESETS.find((p) => p.varName === draft.variable);
    return {
      ...base,
      step: "respond-info",
      respondInfoPresetId: preset?.id ?? CUSTOM_PRESET_ID,
      respondCustomVariable: draft.variable,
      respondDelivery: draft.delivery,
      respondVariable: draft.variable,
      respondTrigger: draft.trigger,
    };
  }
  return { ...base, step: "summary" };
}

export function RuleWizard({
  runtimeVariables,
  existingLabels,
  editingRule,
  onAddVariable,
  onSave,
  onCancel,
}: RuleWizardProps) {
  const initialDraft = useMemo(
    () => (editingRule ? ruleToDraft(editingRule) : null),
    [editingRule]
  );
  const init = useMemo(() => initFromDraft(initialDraft), [initialDraft]);

  const [wizardType, setWizardType] = useState<RuleWizardType | null>(init.wizardType);
  const [step, setStep] = useState<WizardStep>(editingRule ? "summary" : init.step);

  const [captureInfoPresetId, setCaptureInfoPresetId] = useState(init.captureInfoPresetId);
  const [captureCustomOutput, setCaptureCustomOutput] = useState(init.captureCustomOutput);
  const [captureTrigger, setCaptureTrigger] = useState(init.captureTrigger);
  const [captureSave, setCaptureSave] = useState(init.captureSave);
  const [captureOutput, setCaptureOutput] = useState(init.captureOutput);

  const [navigateMode, setNavigateMode] = useState<NavigateWizardDraft["mode"]>(init.navigateMode);
  const [navigateLiteral, setNavigateLiteral] = useState(init.navigateLiteral);
  const [navigateTrigger, setNavigateTrigger] = useState(init.navigateTrigger);
  const [navigateWaitSeconds, setNavigateWaitSeconds] = useState(init.navigateWaitSeconds);

  const [respondInfoPresetId, setRespondInfoPresetId] = useState(init.respondInfoPresetId);
  const [respondCustomVariable, setRespondCustomVariable] = useState(init.respondCustomVariable);
  const [respondDelivery, setRespondDelivery] = useState<RespondWizardDraft["delivery"]>(
    init.respondDelivery
  );
  const [respondVariable, setRespondVariable] = useState(init.respondVariable);
  const [respondTrigger, setRespondTrigger] = useState(init.respondTrigger);
  const [newVariable, setNewVariable] = useState("");

  const draft = useMemo((): WizardDraft | null => {
    if (!wizardType) return null;
    switch (wizardType) {
      case "capture": {
        const output =
          captureInfoPresetId === CUSTOM_PRESET_ID
            ? captureCustomOutput || captureOutput
            : findCapturePreset(captureInfoPresetId)?.outputVar ?? captureOutput;
        const d: CaptureWizardDraft = {
          intent: "capture",
          infoPresetId: captureInfoPresetId,
          customOutput: captureCustomOutput,
          trigger: captureTrigger,
          save: captureSave,
          output: captureSave ? output : "",
        };
        return d;
      }
      case "navigate": {
        const d: NavigateWizardDraft = {
          intent: "navigate",
          mode: navigateMode,
          trigger: navigateTrigger,
          responseLiteral: navigateLiteral,
          waitSeconds: navigateWaitSeconds,
        };
        return d;
      }
      case "respond": {
        const variable =
          respondInfoPresetId === CUSTOM_PRESET_ID
            ? respondCustomVariable || respondVariable
            : findRespondPreset(respondInfoPresetId)?.varName ?? respondVariable;
        const d: RespondWizardDraft = {
          intent: "respond",
          infoPresetId: respondInfoPresetId,
          customVariable: respondCustomVariable,
          delivery: respondDelivery,
          variable,
          trigger: respondTrigger,
        };
        return d;
      }
      case "end":
        return { intent: "end" };
    }
  }, [
    wizardType,
    captureInfoPresetId,
    captureCustomOutput,
    captureTrigger,
    captureSave,
    captureOutput,
    navigateMode,
    navigateLiteral,
    navigateTrigger,
    navigateWaitSeconds,
    respondInfoPresetId,
    respondCustomVariable,
    respondDelivery,
    respondVariable,
    respondTrigger,
  ]);

  const summary = draftSummary(draft);
  const canAdvance = validateDraft(draft);
  const progress = stepProgress(step, wizardType);

  const selectIntent = (type: RuleWizardType) => {
    setWizardType(type);
    if (type === "end") {
      setStep("summary");
      return;
    }
    setStep(firstStepForType(type));
  };

  const resetIntent = () => {
    setWizardType(null);
    setStep("intent");
  };

  const handleSave = () => {
    if (!draft || !validateDraft(draft)) return;
    const labels = existingLabels.filter((l) => l !== editingRule?.label);
    onSave(buildRuleFromDraft(draft, labels, editingRule?.id, editingRule?.label));
  };

  const handleAddVariable = () => {
    const name = newVariable.replace(/\s/g, "_").trim();
    if (!name) return;
    onAddVariable(name);
    setRespondVariable(name);
    setRespondCustomVariable(name);
    setNewVariable("");
  };

  const goNext = () => {
    if (step === "capture-info") setStep("capture-trigger");
    else if (step === "capture-trigger") setStep("capture-save");
    else if (step === "capture-save") setStep("summary");
    else if (step === "navigate-mode") setStep("navigate-action");
    else if (step === "navigate-action") {
      setStep(navigateMode === "wait" ? "summary" : "navigate-trigger");
    } else if (step === "navigate-trigger") setStep("summary");
    else if (step === "respond-info") setStep("respond-delivery");
    else if (step === "respond-delivery") setStep("respond-variable");
    else if (step === "respond-variable") setStep("respond-trigger");
    else if (step === "respond-trigger") setStep("summary");
  };

  const goBack = () => {
    if (step === "summary") {
      if (wizardType === "end") {
        resetIntent();
        return;
      }
      if (wizardType === "capture") setStep("capture-save");
      else if (wizardType === "navigate") {
        setStep(navigateMode === "wait" ? "navigate-action" : "navigate-trigger");
      } else if (wizardType === "respond") setStep("respond-trigger");
      return;
    }
    if (step === "capture-save") setStep("capture-trigger");
    else if (step === "capture-trigger") setStep("capture-info");
    else if (step === "capture-info") resetIntent();
    else if (step === "navigate-trigger") setStep("navigate-action");
    else if (step === "navigate-action") setStep("navigate-mode");
    else if (step === "navigate-mode") resetIntent();
    else if (step === "respond-trigger") setStep("respond-variable");
    else if (step === "respond-variable") setStep("respond-delivery");
    else if (step === "respond-delivery") setStep("respond-info");
    else if (step === "respond-info") resetIntent();
  };

  const selectCapturePreset = (id: string) => {
    setCaptureInfoPresetId(id);
    const preset = findCapturePreset(id);
    if (preset) {
      setCaptureOutput(preset.outputVar);
      if (!captureTrigger) setCaptureTrigger(preset.triggerHint);
    }
    goNext();
  };

  const selectRespondPreset = (id: string) => {
    setRespondInfoPresetId(id);
    const preset = findRespondPreset(id);
    if (preset) {
      setRespondVariable(preset.varName);
      if (!respondTrigger) setRespondTrigger(preset.triggerHint);
    }
    goNext();
  };

  const canProceedFromStep = (): boolean => {
    switch (step) {
      case "capture-info":
        return Boolean(captureInfoPresetId);
      case "capture-trigger":
        return Boolean(captureTrigger.trim());
      case "capture-save":
        return captureSave ? Boolean(captureOutput.trim()) : true;
      case "navigate-mode":
        return true;
      case "navigate-action":
        if (navigateMode === "wait") return navigateWaitSeconds >= 1;
        return Boolean(navigateLiteral.trim());
      case "navigate-trigger":
        return Boolean(navigateTrigger.trim());
      case "respond-info":
        return Boolean(respondInfoPresetId);
      case "respond-delivery":
        return true;
      case "respond-variable":
        return Boolean(respondVariable.trim());
      case "respond-trigger":
        return Boolean(respondTrigger.trim());
      case "summary":
        return validateDraft(draft);
      default:
        return false;
    }
  };

  return (
    <div className="rule-builder rule-wizard">
      <div className="rule-builder-header">
        <h3>{editingRule ? "Edit step" : "Add a step"}</h3>
        <button type="button" className="btn-icon" onClick={onCancel} aria-label="Cancel">
          ×
        </button>
      </div>

      {step !== "intent" && (
        <button type="button" className="rule-builder-back" onClick={goBack}>
          ← Back
        </button>
      )}

      {wizardType && step !== "intent" && (
        <p className="rule-wizard-step-indicator">
          Step {progress.current} of {progress.total}
        </p>
      )}

      {step === "intent" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <div className="intent-grid">
            {INTENTS.map((item) => (
              <button
                key={item.value}
                type="button"
                className="intent-card"
                onClick={() => selectIntent(item.value)}
              >
                <span className="intent-card-label">{item.label}</span>
                <span className="intent-card-hint">{item.hint}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {step === "capture-info" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <div className="intent-grid">
            {CAPTURE_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={`intent-card${captureInfoPresetId === preset.id ? " selected" : ""}`}
                onClick={() => selectCapturePreset(preset.id)}
              >
                <span className="intent-card-label">{preset.label}</span>
                <span className="intent-card-hint">{preset.triggerHint}…</span>
              </button>
            ))}
            <button
              type="button"
              className={`intent-card${captureInfoPresetId === CUSTOM_PRESET_ID ? " selected" : ""}`}
              onClick={() => {
                setCaptureInfoPresetId(CUSTOM_PRESET_ID);
              }}
            >
              <span className="intent-card-label">Custom value</span>
              <span className="intent-card-hint">Define your own field name</span>
            </button>
          </div>
          {captureInfoPresetId === CUSTOM_PRESET_ID && (
            <>
              <label className="rule-builder-field">
                <span>Output variable name</span>
                <input
                  className="editor-input mono"
                  value={captureCustomOutput}
                  onChange={(e) => {
                    setCaptureCustomOutput(e.target.value.replace(/\s/g, "_"));
                    setCaptureOutput(e.target.value.replace(/\s/g, "_"));
                  }}
                  placeholder="custom_field"
                  autoFocus
                />
              </label>
              <div className="rule-builder-actions">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={goNext}
                  disabled={!captureCustomOutput.trim()}
                >
                  Continue
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {step === "capture-trigger" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <p className="field-hint">Trigger phrase</p>
          <div className="intent-grid intent-grid-single">
            {(() => {
              const preset = findCapturePreset(captureInfoPresetId);
              const hints = preset
                ? [preset.triggerHint]
                : ["Your claim status is", "Your balance is"];
              return hints.map((phrase) => (
                <button
                  key={phrase}
                  type="button"
                  className={`intent-card${captureTrigger === phrase ? " selected" : ""}`}
                  onClick={() => setCaptureTrigger(phrase)}
                >
                  <span className="intent-card-label">{phrase}…</span>
                </button>
              ));
            })()}
            <button
              type="button"
              className={`intent-card${!CAPTURE_PRESETS.some((p) => p.triggerHint === captureTrigger) && captureTrigger ? " selected" : ""}`}
              onClick={() => setCaptureTrigger("")}
            >
              <span className="intent-card-label">Custom phrase</span>
            </button>
          </div>
          <label className="rule-builder-field">
            <span>Detection phrase</span>
            <input
              className="editor-input"
              value={captureTrigger}
              onChange={(e) => setCaptureTrigger(e.target.value)}
              placeholder="Your claim status is"
              autoFocus
            />
          </label>
          <div className="rule-builder-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={goNext} disabled={!canProceedFromStep()}>
              Continue
            </button>
          </div>
        </div>
      )}

      {step === "capture-save" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <fieldset className="rule-builder-field">
            <div className="radio-row">
              <label className="radio-pill">
                <input
                  type="radio"
                  name="capture-save"
                  checked={captureSave}
                  onChange={() => setCaptureSave(true)}
                />
                Yes — create output variable
              </label>
              <label className="radio-pill">
                <input
                  type="radio"
                  name="capture-save"
                  checked={!captureSave}
                  onChange={() => setCaptureSave(false)}
                />
                No — listen and continue
              </label>
            </div>
          </fieldset>
          {captureSave && (
            <label className="rule-builder-field">
              <span>Output variable</span>
              <input
                className="editor-input mono"
                value={captureOutput}
                onChange={(e) => setCaptureOutput(e.target.value.replace(/\s/g, "_"))}
                placeholder="claim_status"
              />
              <span className="field-hint mono">{`{{${captureOutput || "field_name"}}}`}</span>
            </label>
          )}
          <div className="rule-builder-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={goNext} disabled={!canProceedFromStep()}>
              Continue
            </button>
          </div>
        </div>
      )}

      {step === "navigate-mode" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <div className="intent-grid">
            {(
              [
                { mode: "keypad" as const, label: "Press a key", hint: "Inject DTMF" },
                { mode: "speak" as const, label: "Speak a phrase", hint: "Text response" },
                { mode: "wait" as const, label: "Wait", hint: "Continue listening" },
              ] as const
            ).map((item) => (
              <button
                key={item.mode}
                type="button"
                className={`intent-card${navigateMode === item.mode ? " selected" : ""}`}
                onClick={() => {
                  setNavigateMode(item.mode);
                  goNext();
                }}
              >
                <span className="intent-card-label">{item.label}</span>
                <span className="intent-card-hint">{item.hint}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {step === "navigate-action" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          {navigateMode === "keypad" && (
            <>
              <p className="field-hint">Key</p>
              <div className="key-grid">
                {NAVIGATE_KEYS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    className={`key-btn${navigateLiteral === key ? " selected" : ""}`}
                    onClick={() => setNavigateLiteral(key)}
                  >
                    {key}
                  </button>
                ))}
              </div>
            </>
          )}
          {navigateMode === "speak" && (
            <label className="rule-builder-field">
              <span>Text response</span>
              <input
                className="editor-input"
                value={navigateLiteral}
                onChange={(e) => setNavigateLiteral(e.target.value)}
                placeholder="Yes"
                autoFocus
              />
            </label>
          )}
          {navigateMode === "wait" && (
            <label className="rule-builder-field">
              <span>How long should the assistant wait?</span>
              <div className="wait-input-row">
                <input
                  className="editor-input"
                  type="number"
                  min={1}
                  max={120}
                  value={navigateWaitSeconds}
                  onChange={(e) => setNavigateWaitSeconds(Number(e.target.value))}
                  autoFocus
                />
                <span className="wait-suffix">seconds</span>
              </div>
            </label>
          )}
          <div className="rule-builder-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={goNext} disabled={!canProceedFromStep()}>
              Continue
            </button>
          </div>
        </div>
      )}

      {step === "navigate-trigger" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <p className="field-hint">Trigger phrase</p>
          <div className="intent-grid intent-grid-single">
            {NAVIGATE_TRIGGER_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={`intent-card${navigateTrigger === preset.phrase ? " selected" : ""}`}
                onClick={() => setNavigateTrigger(preset.phrase)}
              >
                <span className="intent-card-label">{preset.label}…</span>
              </button>
            ))}
            <button type="button" className="intent-card" onClick={() => setNavigateTrigger("")}>
              <span className="intent-card-label">Custom phrase</span>
            </button>
          </div>
          <label className="rule-builder-field">
            <span>Detection phrase</span>
            <input
              className="editor-input"
              value={navigateTrigger}
              onChange={(e) => setNavigateTrigger(e.target.value)}
              placeholder="For billing"
              autoFocus
            />
          </label>
          <div className="rule-builder-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={goNext} disabled={!canProceedFromStep()}>
              Continue
            </button>
          </div>
        </div>
      )}

      {step === "respond-info" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <div className="intent-grid">
            {RESPOND_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                className={`intent-card${respondInfoPresetId === preset.id ? " selected" : ""}`}
                onClick={() => selectRespondPreset(preset.id)}
              >
                <span className="intent-card-label">{preset.label}</span>
                <span className="intent-card-hint">{preset.triggerHint}</span>
              </button>
            ))}
            <button
              type="button"
              className={`intent-card${respondInfoPresetId === CUSTOM_PRESET_ID ? " selected" : ""}`}
              onClick={() => setRespondInfoPresetId(CUSTOM_PRESET_ID)}
            >
              <span className="intent-card-label">Custom value</span>
            </button>
          </div>
          {respondInfoPresetId === CUSTOM_PRESET_ID && (
            <>
              <label className="rule-builder-field">
                <span>Variable name</span>
                <input
                  className="editor-input mono"
                  value={respondCustomVariable}
                  onChange={(e) => {
                    setRespondCustomVariable(e.target.value.replace(/\s/g, "_"));
                    setRespondVariable(e.target.value.replace(/\s/g, "_"));
                  }}
                  placeholder="custom_field"
                  autoFocus
                />
              </label>
              <div className="rule-builder-actions">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={goNext}
                  disabled={!respondCustomVariable.trim()}
                >
                  Continue
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {step === "respond-delivery" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <fieldset className="rule-builder-field">
            <div className="radio-row">
              <label className="radio-pill">
                <input
                  type="radio"
                  name="respond-delivery"
                  checked={respondDelivery === "keypad"}
                  onChange={() => setRespondDelivery("keypad")}
                />
                Touchtones (DTMF)
              </label>
              <label className="radio-pill">
                <input
                  type="radio"
                  name="respond-delivery"
                  checked={respondDelivery === "speak"}
                  onChange={() => setRespondDelivery("speak")}
                />
                Speech
              </label>
            </div>
          </fieldset>
          <div className="rule-builder-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={goNext}>
              Continue
            </button>
          </div>
        </div>
      )}

      {step === "respond-variable" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <label className="rule-builder-field">
            <span>Which value should it use?</span>
            {runtimeVariables.length > 0 ? (
              <select
                className="editor-input mono"
                value={respondVariable}
                onChange={(e) => setRespondVariable(e.target.value)}
              >
                {runtimeVariables.map((v) => (
                  <option key={v} value={v}>
                    {`{{${v}}}`}
                  </option>
                ))}
              </select>
            ) : (
              <p className="field-hint warn">Add a run value in Setup, or create one below.</p>
            )}
          </label>
          <div className="rule-builder-inline-add">
            <input
              className="editor-input mono"
              value={newVariable}
              onChange={(e) => setNewVariable(e.target.value.replace(/\s/g, "_"))}
              placeholder="new_value_name"
            />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleAddVariable}
              disabled={!newVariable.trim()}
            >
              Add value
            </button>
          </div>
          <div className="rule-builder-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={goNext} disabled={!canProceedFromStep()}>
              Continue
            </button>
          </div>
        </div>
      )}

      {step === "respond-trigger" && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <p className="field-hint">Trigger phrase</p>
          <div className="intent-grid intent-grid-single">
            {(() => {
              const preset = findRespondPreset(respondInfoPresetId);
              const hints = preset
                ? [preset.triggerHint]
                : RESPOND_PRESETS.map((p) => p.triggerHint).slice(0, 2);
              return hints.map((phrase) => (
                <button
                  key={phrase}
                  type="button"
                  className={`intent-card${respondTrigger === phrase ? " selected" : ""}`}
                  onClick={() => setRespondTrigger(phrase)}
                >
                  <span className="intent-card-label">{phrase}</span>
                </button>
              ));
            })()}
            <button type="button" className="intent-card" onClick={() => setRespondTrigger("")}>
              <span className="intent-card-label">Custom phrase</span>
            </button>
          </div>
          <label className="rule-builder-field">
            <span>Detection phrase</span>
            <input
              className="editor-input"
              value={respondTrigger}
              onChange={(e) => setRespondTrigger(e.target.value)}
              placeholder="Please enter your account number"
              autoFocus
            />
          </label>
          <div className="rule-builder-actions">
            <button type="button" className="btn btn-primary btn-sm" onClick={goNext} disabled={!canProceedFromStep()}>
              Continue
            </button>
          </div>
        </div>
      )}

      {step === "summary" && summary && (
        <div className="rule-builder-step">
          <p className="rule-builder-prompt">{stepLabel(step, wizardType)}</p>
          <div className="rule-wizard-summary">
            <div className="rule-wizard-summary-row">
              <span className="rule-wizard-summary-key">Type</span>
              <span className="rule-wizard-summary-val">{summary.typeLabel}</span>
            </div>
            {summary.trigger && summary.trigger !== "—" && (
              <div className="rule-wizard-summary-row">
                <span className="rule-wizard-summary-key">Trigger</span>
                <span className="rule-wizard-summary-val">{summary.trigger}</span>
              </div>
            )}
            <div className="rule-wizard-summary-row">
              <span className="rule-wizard-summary-key">Action</span>
              <span className="rule-wizard-summary-val">{summary.action}</span>
            </div>
            {summary.inputVariable && (
              <div className="rule-wizard-summary-row">
                <span className="rule-wizard-summary-key">Input</span>
                <span className="rule-wizard-summary-val mono">{summary.inputVariable}</span>
              </div>
            )}
            {summary.outputVariable && (
              <div className="rule-wizard-summary-row">
                <span className="rule-wizard-summary-key">Output</span>
                <span className="rule-wizard-summary-val mono">{summary.outputVariable}</span>
              </div>
            )}
          </div>
          {wizardType && (
            <button type="button" className="rule-builder-back" onClick={resetIntent}>
              ← Change action
            </button>
          )}
          <div className="rule-builder-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={onCancel}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleSave}
              disabled={!canAdvance}
            >
              {editingRule ? "Save changes" : "Add step"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
