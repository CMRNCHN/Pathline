import type {
  ExtractedSchemaField,
  FlowStep,
  IvrRule,
  ScriptDocument,
  ScriptSetup,
} from "./types";
import { SCRIPT_VERSION } from "./types";
import { migrateV1ToV2 } from "./migrate";
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
  };
}

function normalizeIvrRule(raw: Partial<IvrRule>): IvrRule {
  return {
    id: raw.id ?? newId(),
    label: raw.label ?? "",
    valueReference: raw.valueReference ?? "",
    expectedInput: raw.expectedInput ?? "",
    rule: raw.rule ?? "",
  };
}

function normalizeFlowStep(raw: Partial<FlowStep>): FlowStep {
  return {
    id: raw.id ?? newId(),
    detect: raw.detect ?? "",
    action: raw.action ?? "pass",
    triggerLabel: raw.triggerLabel,
    extractField: raw.extractField,
    map: raw.map?.map((m) => ({
      id: m.id ?? newId(),
      detect: m.detect ?? "",
      value: m.value ?? "",
    })),
  };
}

function normalizeSchemaField(raw: Partial<ExtractedSchemaField>): ExtractedSchemaField {
  return {
    id: raw.id ?? newId(),
    field: raw.field ?? "",
    type: raw.type ?? "text",
  };
}

function normalizeV2(raw: unknown): ScriptDocument {
  const o = raw as Partial<ScriptDocument>;
  return {
    id: o.id ?? newId(),
    version: SCRIPT_VERSION,
    setup: normalizeSetup(o.setup ?? {}),
    ivrRules: (o.ivrRules ?? []).map(normalizeIvrRule),
    conversationFlow: (o.conversationFlow ?? []).map(normalizeFlowStep),
    extractedSchema: (o.extractedSchema ?? []).map(normalizeSchemaField),
  };
}

export function normalizeScript(raw: unknown): ScriptDocument {
  if (isV2Shape(raw)) return normalizeV2(raw);
  return migrateV1ToV2(raw);
}

const VAR_REF = /\{\{(\w+)\}\}/g;

export function extractVariableNames(doc: ScriptDocument): string[] {
  const names = new Set<string>();
  for (const rule of doc.ivrRules) {
    for (const m of rule.valueReference.matchAll(VAR_REF)) {
      names.add(m[1]);
    }
  }
  return [...names].sort();
}

export function resolveReference(template: string, variables: Record<string, string>): string {
  return template.replace(VAR_REF, (_, key: string) => variables[key] ?? `{{${key}}}`);
}

export function newIvrRule(): IvrRule {
  return {
    id: newId(),
    label: "",
    valueReference: "",
    expectedInput: "",
    rule: "Inject DTMF after detect",
  };
}

export function newFlowStep(action: FlowStep["action"] = "trigger"): FlowStep {
  return { id: newId(), detect: "", action, map: action === "extract" ? [] : undefined };
}

export function newSchemaField(): ExtractedSchemaField {
  return { id: newId(), field: "", type: "text" };
}

export function newMapEntry(): { id: string; detect: string; value: string } {
  return { id: newId(), detect: "", value: "" };
}

export function findIvrRule(doc: ScriptDocument, label: string): IvrRule | undefined {
  return doc.ivrRules.find((r) => r.label === label);
}

export function applyExtractMap(phrase: string, map: { detect: string; value: string }[]): string | undefined {
  const hay = phrase.toLowerCase();
  for (const entry of map) {
    const needle = entry.detect.trim().toLowerCase();
    if (needle && hay.includes(needle)) return entry.value;
  }
  return undefined;
}
