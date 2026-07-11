/** Runtime rule format — compiled from ScriptDocument for execution */
export interface StatusRule {
  trigger?: string;
  response: string;
  key: string;
  status: string;
  dtmf?: string;
  endCall?: boolean;
}

export type ScriptAction =
  | "send_keys"
  | "save_value"
  | "speak"
  | "wait"
  | "hang_up"
  | "jump";

export const ACTION_LABELS: Record<ScriptAction, string> = {
  send_keys: "Send Keys",
  save_value: "Save Value",
  speak: "Speak",
  wait: "Wait",
  hang_up: "Hang Up",
  jump: "Jump",
};

export interface ScriptSecret {
  id: string;
  name: string;
  description: string;
  example: string;
  required: boolean;
}

export interface CapturedValue {
  id: string;
  key: string;
  description: string;
}

export interface ConversationStep {
  id: string;
  listenFor: string;
  action: ScriptAction;
  keys?: string;
  resultKey?: string;
  value?: string;
  speakText?: string;
  waitMs?: number;
  jumpToStepId?: string;
}

export interface ScriptDocument {
  id: string;
  name: string;
  description: string;
  target: string;
  timeoutMs: number;
  tags: string[];
  setupComplete: boolean;
  secrets: ScriptSecret[];
  conversation: ConversationStep[];
  results: CapturedValue[];
  /** @deprecated Legacy — migrated on load */
  rules?: StatusRule[];
}

/** Alias used across the app */
export type KnownScript = ScriptDocument;

export type EditorSection = "basics" | "secrets" | "conversation" | "results";
