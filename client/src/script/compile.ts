import type { FlowStep, IvrRule, ScriptDocument, ScriptSetup } from "./types";
import { SCRIPT_VERSION } from "./types";
import { migrateV1ToV2 } from "./migrate";
import { syncRuntimeVariablesFromRules, withSyncedRules } from "./sync";
import { newId } from "./storage";

function isV2Shape(raw: unknown): boolean {
  const o = raw as Record<string, unknown>;
  return o.version === SCRIPT_VERSION || (Boolean(o.setup) && Array.isArray(o.ivrRules));
}

function normalizeSetup(raw: Partial<ScriptSetup>): ScriptSetup {
  return {
    name: raw.name ?? "",
    description: raw.description ?? "",
    target: raw.target ?? "",
    timeoutMs: raw.timeoutMs ?? 30000,
    speechPreferences: {
      autoListen: raw.speechPreferences?.autoListen ?? false,
    },
    runtimeVariables: (raw.runtimeVariables ?? []).filter(Boolean),
  };
}

function normalizeIvrRule(raw: Partial<IvrRule> & { expectedInput?: string; valueReference?: string }): IvrRule {
  return {
    id: raw.id ?? newId(),
    label: raw.label ?? "",
    trigger: raw.trigger ?? raw.expectedInput ?? "",
    response: raw.response ?? raw.valueReference ?? "",
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
  ivrRules: IvrRule[],
  conversationFlow: FlowStep[],
  legacySchemaFields: string[]
): { ivrRules: IvrRule[]; conversationFlow: FlowStep[] } {
  let rules = [...ivrRules];
  const flow = conversationFlow.map((step) => {
    if (step.action !== "extract" || !step.triggerLabel) return step;

    const legacyField =
      step.triggerLabel && !rules.some((r) => r.label === step.triggerLabel)
        ? step.triggerLabel
        : undefined;

    const fieldName =
      legacyField ??
      rules.find((r) => r.label === step.triggerLabel)?.output ??
      step.triggerLabel ??
      "";

    let rule =
      rules.find((r) => r.label === step.triggerLabel) ??
      rules.find((r) => r.output === fieldName);

    if (!rule && fieldName) {
      rule = {
        id: newId(),
        label: fieldName,
        trigger: step.detect,
        response: "",
        rule: "Capture value after detect",
        output: fieldName,
      };
      rules = [...rules, rule];
    } else if (rule && !rule.output && fieldName) {
      rules = rules.map((r) => (r.id === rule!.id ? { ...r, output: fieldName } : r));
    }

    return {
      ...step,
      triggerLabel: rule?.label ?? step.triggerLabel,
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
          trigger: "",
          response: "",
          rule: "Capture value after detect",
          output: field,
        },
      ];
    }
  }

  return { ivrRules: rules, conversationFlow: flow };
}

function normalizeV2(raw: unknown): ScriptDocument {
  const o = raw as Partial<ScriptDocument> & {
    extractedSchema?: { field?: string }[];
  };

  let ivrRules = (o.ivrRules ?? []).map(normalizeIvrRule);
  let conversationFlow = (o.conversationFlow ?? []).map(normalizeFlowStep);

  const legacySchemaFields = (o.extractedSchema ?? []).map((f) => f.field ?? "").filter(Boolean);
  if (legacySchemaFields.length || conversationFlow.some((s) => s.action === "extract")) {
    const migrated = migrateLegacyExtracts(ivrRules, conversationFlow, legacySchemaFields);
    ivrRules = migrated.ivrRules;
    conversationFlow = migrated.conversationFlow;
  }

  const doc: ScriptDocument = {
    id: o.id ?? newId(),
    version: SCRIPT_VERSION,
    setup: normalizeSetup(o.setup ?? {}),
    ivrRules,
    conversationFlow,
  };

  return {
    ...doc,
    ...withSyncedRules(doc, ivrRules),
  };
}

export function normalizeScript(raw: unknown): ScriptDocument {
  if (isV2Shape(raw)) return normalizeV2(raw);
  return migrateV1ToV2(raw);
}

const VAR_REF = /\{\{(\w+)\}\}/g;

/** Input variable names required at run time — always derived from rules, never from setup. */
export function extractVariableNames(doc: ScriptDocument): string[] {
  return syncRuntimeVariablesFromRules(doc.ivrRules);
}

export function formatVariableRef(name: string): string {
  return `{{${name}}}`;
}

export function resolveReference(template: string, variables: Record<string, string>): string {
  return template.replace(VAR_REF, (_, key: string) => variables[key] ?? `{{${key}}}`);
}

export function newIvrRule(index: number): IvrRule {
  return {
    id: newId(),
    label: `rule_${index}`,
    trigger: "",
    response: "",
    rule: "Inject DTMF after detect",
    output: "",
  };
}

export function newFlowStep(action: FlowStep["action"] = "trigger"): FlowStep {
  return { id: newId(), detect: "", action };
}

export function findIvrRule(doc: ScriptDocument, label: string): IvrRule | undefined {
  return doc.ivrRules.find((r) => r.label === label);
}

export function extractOutputRules(doc: ScriptDocument): IvrRule[] {
  return doc.ivrRules.filter((r) => r.label.trim() && r.output.trim());
}

export { syncConversationFlowFromRules, syncRuntimeVariablesFromRules, withSyncedRules } from "./sync";
