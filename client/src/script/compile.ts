import type {
  CapturedValue,
  ConversationStep,
  ScriptAction,
  ScriptDocument,
  ScriptSecret,
  StatusRule,
} from "./types";
import { newId } from "./storage";

function stepFromSend(trigger: string, dtmf: string): ConversationStep {
  return { id: newId(), listenFor: trigger, action: "send_keys", keys: dtmf };
}

function stepFromSave(response: string, key: string, status: string, endCall: boolean): ConversationStep[] {
  const steps: ConversationStep[] = [
    { id: newId(), listenFor: response, action: "save_value", resultKey: key, value: status },
  ];
  if (endCall) steps.push({ id: newId(), listenFor: "", action: "hang_up" });
  return steps;
}

export function migrateLegacyRules(rules: StatusRule[]): ConversationStep[] {
  const steps: ConversationStep[] = [];
  for (const rule of rules) {
    const isSend = Boolean(rule.trigger?.trim() || rule.dtmf?.trim());
    if (isSend) {
      steps.push(stepFromSend(rule.trigger ?? "", rule.dtmf ?? ""));
    } else if (rule.response?.trim()) {
      steps.push(...stepFromSave(rule.response, rule.key, rule.status, Boolean(rule.endCall)));
    } else if (rule.endCall) {
      steps.push({ id: newId(), listenFor: "", action: "hang_up" });
    }
  }
  return steps;
}

function migrateSecrets(raw: unknown): ScriptSecret[] {
  if (!Array.isArray(raw)) return [];
  if (raw.length === 0) return [];
  if (typeof raw[0] === "string") {
    return (raw as string[]).map((name) => ({
      id: newId(),
      name,
      description: "",
      example: "",
      required: true,
    }));
  }
  return raw as ScriptSecret[];
}

function inferResults(conversation: ConversationStep[]): CapturedValue[] {
  const keys = new Map<string, CapturedValue>();
  for (const step of conversation) {
    if (step.action === "save_value" && step.resultKey) {
      if (!keys.has(step.resultKey)) {
        keys.set(step.resultKey, {
          id: newId(),
          key: step.resultKey,
          description: "",
        });
      }
    }
  }
  return [...keys.values()];
}

export function normalizeScript(raw: unknown): ScriptDocument {
  const o = raw as Partial<ScriptDocument> & { rules?: StatusRule[]; secrets?: unknown };

  let conversation = o.conversation ?? [];
  if (conversation.length === 0 && o.rules?.length) {
    conversation = migrateLegacyRules(o.rules);
  }

  const secrets = migrateSecrets(o.secrets);
  const results = o.results?.length ? o.results : inferResults(conversation);

  return {
    id: o.id ?? newId(),
    name: o.name ?? "New script",
    description: o.description ?? "",
    target: o.target ?? "",
    timeoutMs: o.timeoutMs ?? 30000,
    tags: o.tags ?? [],
    setupComplete: o.setupComplete ?? Boolean(o.name && o.target),
    secrets,
    conversation,
    results,
  };
}

export function compileToRules(doc: ScriptDocument): StatusRule[] {
  const rules: StatusRule[] = [];

  for (let i = 0; i < doc.conversation.length; i++) {
    const step = doc.conversation[i];
    const next = doc.conversation[i + 1];
    const endsNext = next?.action === "hang_up";

    switch (step.action) {
      case "send_keys":
        if (step.listenFor?.trim() || step.keys?.trim()) {
          rules.push({
            trigger: step.listenFor ?? "",
            response: "",
            key: "",
            status: "",
            dtmf: step.keys ?? "",
            endCall: false,
          });
        }
        break;

      case "save_value":
        if (step.listenFor?.trim()) {
          rules.push({
            trigger: "",
            response: step.listenFor,
            key: step.resultKey ?? "",
            status: step.value ?? "",
            endCall: endsNext,
          });
        }
        break;

      case "hang_up":
        if (step.listenFor?.trim()) {
          rules.push({
            trigger: "",
            response: step.listenFor,
            key: "_ended",
            status: "ended",
            endCall: true,
          });
        }
        break;

      case "speak":
      case "wait":
      case "jump":
        break;
    }
  }

  const last = doc.conversation[doc.conversation.length - 1];
  if (last?.action === "hang_up" && !last.listenFor?.trim() && rules.length > 0) {
    rules[rules.length - 1] = { ...rules[rules.length - 1], endCall: true };
  }

  return rules;
}

export function requiredSecretNames(doc: ScriptDocument): string[] {
  const fromDefs = doc.secrets.filter((s) => s.required).map((s) => s.name);
  const fromPlaceholders = new Set<string>();
  for (const step of doc.conversation) {
    if (step.keys) {
      for (const m of step.keys.matchAll(/\{(\w+)\}/g)) fromPlaceholders.add(m[1]);
    }
  }
  return [...new Set([...fromDefs, ...fromPlaceholders])].filter(Boolean);
}

export function actionLabel(action: ScriptAction): string {
  const labels: Record<ScriptAction, string> = {
    send_keys: "Send Keys",
    save_value: "Save",
    speak: "Speak",
    wait: "Wait",
    hang_up: "End Call",
    jump: "Jump",
  };
  return labels[action];
}

export function newConversationStep(action: ScriptAction = "send_keys"): ConversationStep {
  return { id: newId(), listenFor: "", action, keys: action === "send_keys" ? "" : undefined };
}

export function newSecret(): ScriptSecret {
  return { id: newId(), name: "", description: "", example: "", required: true };
}

export function newResult(): CapturedValue {
  return { id: newId(), key: "", description: "" };
}
