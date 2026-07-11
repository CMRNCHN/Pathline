import type { FlowStep, Step, PathDocument, PathSetup } from "./types";
import { SCRIPT_VERSION } from "./types";
import { migrateV1ToV2 } from "./migrate";
import { withSyncedRules } from "./sync";
import { newId } from "./storage";

/** Legacy field aliases accepted on load (pre-Pathline field keys). */
type LegacySetup = Partial<PathSetup> & { runtimeVariables?: string[] };
type LegacyStep = Partial<Step> & {
  trigger?: string;
  response?: string;
  expectedInput?: string;
  valueReference?: string;
};
type LegacyDoc = Partial<PathDocument> & {
  ivrRules?: LegacyStep[];
  extractedSchema?: { field?: string }[];
};

function isV2Shape(raw: unknown): boolean {
  const o = raw as Record<string, unknown>;
  return (
    o.version === SCRIPT_VERSION ||
    (Boolean(o.setup) && (Array.isArray(o.steps) || Array.isArray(o.ivrRules)))
  );
}

function normalizeSetup(raw: LegacySetup): PathSetup {
  return {
    name: raw.name ?? "",
    description: raw.description ?? "",
    target: raw.target ?? "",
    timeoutMs: raw.timeoutMs ?? 30000,
    speechPreferences: {
      autoListen: raw.speechPreferences?.autoListen ?? false,
    },
    inputs: (raw.inputs ?? raw.runtimeVariables ?? []).filter(Boolean),
  };
}

function normalizeStep(raw: LegacyStep): Step {
  return {
    id: raw.id ?? newId(),
    label: raw.label ?? "",
    when: raw.when ?? raw.trigger ?? raw.expectedInput ?? "",
    then: raw.then ?? raw.response ?? raw.valueReference ?? "",
    rule: raw.rule ?? "Inject DTMF after detect",
    output: raw.output ?? "",
    waitSeconds: raw.waitSeconds,
  };
}

type LegacyFlowStep = Partial<FlowStep> & {
  extractField?: string;
  extractLabel?: string;
};

function normalizeFlowStep(raw: LegacyFlowStep): FlowStep {
  return {
    id: raw.id ?? newId(),
    detect: raw.detect ?? "",
    action: raw.action ?? "pass",
    triggerLabel: raw.triggerLabel ?? raw.extractLabel ?? raw.extractField,
  };
}

function migrateLegacyExtracts(
  steps: Step[],
  conversationFlow: FlowStep[],
  legacySchemaFields: string[]
): { steps: Step[]; conversationFlow: FlowStep[] } {
  let rules = [...steps];
  const flow = conversationFlow.map((flowStep) => {
    if (flowStep.action !== "extract" || !flowStep.triggerLabel) return flowStep;

    const legacyField =
      flowStep.triggerLabel && !rules.some((r) => r.label === flowStep.triggerLabel)
        ? flowStep.triggerLabel
        : undefined;

    const fieldName =
      legacyField ??
      rules.find((r) => r.label === flowStep.triggerLabel)?.output ??
      flowStep.triggerLabel ??
      "";

    let step =
      rules.find((r) => r.label === flowStep.triggerLabel) ??
      rules.find((r) => r.output === fieldName);

    if (!step && fieldName) {
      step = {
        id: newId(),
        label: fieldName,
        when: flowStep.detect,
        then: "",
        rule: "Capture value after detect",
        output: fieldName,
      };
      rules = [...rules, step];
    } else if (step && !step.output && fieldName) {
      rules = rules.map((r) => (r.id === step!.id ? { ...r, output: fieldName } : r));
    }

    return {
      ...flowStep,
      triggerLabel: step?.label ?? flowStep.triggerLabel,
    };
  });

  for (const field of legacySchemaFields) {
    if (!field.trim()) continue;
    if (!rules.some((r) => r.output === field)) {
      rules = [
        ...rules,
        {
          id: newId(),
          label: field,
          when: "",
          then: "",
          rule: "Capture value after detect",
          output: field,
        },
      ];
    }
  }

  return { steps: rules, conversationFlow: flow };
}

function normalizeV2(raw: unknown): PathDocument {
  const o = raw as LegacyDoc;

  const rawSteps = o.steps ?? o.ivrRules ?? [];
  let steps = rawSteps.map(normalizeStep);
  let conversationFlow = (o.conversationFlow ?? []).map(normalizeFlowStep);

  const legacySchemaFields = (o.extractedSchema ?? []).map((f) => f.field ?? "").filter(Boolean);
  if (legacySchemaFields.length || conversationFlow.some((s) => s.action === "extract")) {
    const migrated = migrateLegacyExtracts(steps, conversationFlow, legacySchemaFields);
    steps = migrated.steps;
    conversationFlow = migrated.conversationFlow;
  }

  const doc: PathDocument = {
    id: o.id ?? newId(),
    version: SCRIPT_VERSION,
    setup: normalizeSetup(o.setup ?? {}),
    steps,
    conversationFlow,
  };

  return {
    ...doc,
    ...withSyncedRules(doc, steps),
  };
}

export function normalizeScript(raw: unknown): PathDocument {
  if (isV2Shape(raw)) return normalizeV2(raw);
  return migrateV1ToV2(raw);
}

const VAR_REF = /\{\{(\w+)\}\}/g;

export function extractVariableNames(doc: PathDocument): string[] {
  const fromSetup = doc.setup.inputs.filter(Boolean);
  if (fromSetup.length) return [...fromSetup].sort();

  const names = new Set<string>();
  for (const step of doc.steps) {
    for (const m of step.then.matchAll(VAR_REF)) {
      names.add(m[1]);
    }
  }
  return [...names].sort();
}

export function formatVariableRef(name: string): string {
  return `{{${name}}}`;
}

export function resolveReference(template: string, variables: Record<string, string>): string {
  return template.replace(VAR_REF, (_, key: string) => variables[key] ?? `{{${key}}}`);
}

export function newIvrRule(index: number): Step {
  return {
    id: newId(),
    label: `rule_${index}`,
    when: "",
    then: "",
    rule: "Inject DTMF after detect",
    output: "",
  };
}

export function newFlowStep(action: FlowStep["action"] = "trigger"): FlowStep {
  return { id: newId(), detect: "", action };
}

export function findIvrRule(doc: PathDocument, label: string): Step | undefined {
  return doc.steps.find((r) => r.label === label);
}

export function extractOutputRules(doc: PathDocument): Step[] {
  return doc.steps.filter((r) => r.label.trim() && r.output.trim());
}

export { syncConversationFlowFromRules, syncInputsFromSteps, withSyncedRules } from "./sync";
