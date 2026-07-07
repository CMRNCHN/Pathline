import type {
  ExtractedSchemaField,
  FlowStep,
  IvrRule,
  ScriptDocument,
  ScriptSetup,
} from "./types";
import { SCRIPT_VERSION } from "./types";
import { newId } from "./storage";

/** v1 shape — used only for one-time migration. */
interface V1ConversationStep {
  id?: string;
  listenFor?: string;
  action?: string;
  keys?: string;
  resultKey?: string;
  value?: string;
}

interface V1StatusRule {
  trigger?: string;
  response?: string;
  key?: string;
  status?: string;
  dtmf?: string;
  endCall?: boolean;
}

interface V1Document {
  id?: string;
  name?: string;
  description?: string;
  target?: string;
  timeoutMs?: number;
  secrets?: unknown;
  conversation?: V1ConversationStep[];
  results?: { id?: string; key?: string; description?: string }[];
  rules?: V1StatusRule[];
}

function slugLabel(prefix: string, index: number): string {
  return `${prefix}_${index}`;
}

function toValueReference(keys: string, index: number): string {
  if (!keys.trim()) return `{{dtmf_${index}}}`;
  const doubled = keys.replace(/\{(\w+)\}/g, "{{$1}}");
  if (doubled.includes("{{")) return doubled;
  return `{{dtmf_${index}}}`;
}

function migrateLegacyRulesToFlow(rules: V1StatusRule[]): {
  ivrRules: IvrRule[];
  conversationFlow: FlowStep[];
  schema: Map<string, ExtractedSchemaField>;
} {
  const ivrRules: IvrRule[] = [];
  const conversationFlow: FlowStep[] = [];
  const schema = new Map<string, ExtractedSchemaField>();
  let ruleIndex = 0;

  for (const rule of rules) {
    const isSend = Boolean(rule.trigger?.trim() || rule.dtmf?.trim());
    if (isSend) {
      ruleIndex += 1;
      const label = slugLabel("rule", ruleIndex);
      ivrRules.push({
        id: newId(),
        label,
        valueReference: toValueReference(rule.dtmf ?? "", ruleIndex),
        expectedInput: rule.trigger ?? "",
        rule: "Inject DTMF after detect",
      });
      conversationFlow.push({
        id: newId(),
        detect: rule.trigger ?? "",
        action: "trigger",
        triggerLabel: label,
      });
    } else if (rule.response?.trim()) {
      const field = rule.key?.trim() || slugLabel("field", ruleIndex + 1);
      if (!schema.has(field)) {
        schema.set(field, { id: newId(), field, type: "text" });
      }
      const map = rule.status
        ? [{ id: newId(), detect: rule.status.toLowerCase(), value: rule.status }]
        : [];
      conversationFlow.push({
        id: newId(),
        detect: rule.response,
        action: "extract",
        extractField: field,
        map,
      });
      if (rule.endCall) {
        conversationFlow.push({ id: newId(), detect: rule.response, action: "end" });
      }
    } else if (rule.endCall) {
      conversationFlow.push({ id: newId(), detect: "", action: "end" });
    }
  }

  return { ivrRules, conversationFlow, schema };
}

export function migrateV1ToV2(raw: unknown): ScriptDocument {
  const o = raw as V1Document;

  const setup: ScriptSetup = {
    name: o.name ?? "",
    description: o.description ?? "",
    target: o.target ?? "",
    timeoutMs: o.timeoutMs ?? 30000,
    speechPreferences: { autoListen: false },
  };

  let ivrRules: IvrRule[] = [];
  let conversationFlow: FlowStep[] = [];
  const schema = new Map<string, ExtractedSchemaField>();

  let conversation = o.conversation ?? [];
  if (conversation.length === 0 && o.rules?.length) {
    const migrated = migrateLegacyRulesToFlow(o.rules);
    ivrRules = migrated.ivrRules;
    conversationFlow = migrated.conversationFlow;
    for (const [k, v] of migrated.schema) schema.set(k, v);
  } else {
    let ruleIndex = 0;
    for (const step of conversation) {
      if (step.action === "send_keys") {
        ruleIndex += 1;
        const label = slugLabel("rule", ruleIndex);
        ivrRules.push({
          id: newId(),
          label,
          valueReference: toValueReference(step.keys ?? "", ruleIndex),
          expectedInput: step.listenFor ?? "",
          rule: "Inject DTMF after detect",
        });
        conversationFlow.push({
          id: step.id ?? newId(),
          detect: step.listenFor ?? "",
          action: "trigger",
          triggerLabel: label,
        });
      } else if (step.action === "save_value") {
        const field = step.resultKey?.trim() || slugLabel("field", ruleIndex + 1);
        if (!schema.has(field)) {
          schema.set(field, { id: newId(), field, type: "text" });
        }
        const map = step.value
          ? [{ id: newId(), detect: step.value.toLowerCase(), value: step.value }]
          : [];
        conversationFlow.push({
          id: step.id ?? newId(),
          detect: step.listenFor ?? "",
          action: "extract",
          extractField: field,
          map,
        });
      } else if (step.action === "hang_up") {
        conversationFlow.push({
          id: step.id ?? newId(),
          detect: step.listenFor ?? "",
          action: "end",
        });
      } else if (step.action === "wait" || step.listenFor?.trim()) {
        conversationFlow.push({
          id: step.id ?? newId(),
          detect: step.listenFor ?? "",
          action: "pass",
        });
      }
    }
  }

  for (const r of o.results ?? []) {
    if (r.key?.trim() && !schema.has(r.key)) {
      schema.set(r.key, { id: r.id ?? newId(), field: r.key, type: "text" });
    }
  }

  return {
    id: o.id ?? newId(),
    version: SCRIPT_VERSION,
    setup,
    ivrRules,
    conversationFlow,
    extractedSchema: [...schema.values()],
  };
}
