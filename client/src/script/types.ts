export const SCRIPT_VERSION = 2 as const;

export type SchemaFieldType = "text" | "currency" | "number";

export type FlowAction = "trigger" | "extract" | "end" | "pass";

export interface ScriptSetup {
  name: string;
  description: string;
  target: string;
  timeoutMs: number;
  speechPreferences: {
    autoListen: boolean;
  };
}

export interface IvrRule {
  id: string;
  label: string;
  valueReference: string;
  expectedInput: string;
  rule: string;
}

export interface ExtractMapEntry {
  id: string;
  detect: string;
  value: string;
}

export interface FlowStep {
  id: string;
  detect: string;
  action: FlowAction;
  triggerLabel?: string;
  extractField?: string;
  map?: ExtractMapEntry[];
}

export interface ExtractedSchemaField {
  id: string;
  field: string;
  type: SchemaFieldType;
}

export interface ScriptDocument {
  id: string;
  version: typeof SCRIPT_VERSION;
  setup: ScriptSetup;
  ivrRules: IvrRule[];
  conversationFlow: FlowStep[];
  extractedSchema: ExtractedSchemaField[];
}

/** Runtime values for a single run — never stored in the template. */
export interface RunConfiguration {
  target: string;
  variables: Record<string, string>;
  runtimeOptions: {
    autoListen: boolean;
  };
}

/** Output produced when a run completes. */
export interface ExportPackage {
  sessionId: string;
  scriptId: string;
  scriptName: string;
  extractedData: Record<string, string>;
  activity: RunLogEntry[];
  completedAt: string;
}

export interface RunLogEntry {
  at: string;
  message: string;
  kind: "trigger" | "extract" | "pass" | "end" | "unknown" | "info";
}

export interface RunState {
  collected: Record<string, string>;
  log: RunLogEntry[];
  lastPhrase?: string;
  pendingDtmf?: string;
  pendingTrigger?: string;
  completed: boolean;
}

export type KnownScript = ScriptDocument;
