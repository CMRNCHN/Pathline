export interface StatusRule {
  /** Phrase that prompts a DTMF action */
  trigger?: string;
  /** IVR phrase to match for status capture */
  response: string;
  /** JSON key in the collected status object */
  key: string;
  /** Value assigned when response matches */
  status: string;
  /** DTMF to send when trigger matches */
  dtmf?: string;
  endCall?: boolean;
}

export interface KnownScript {
  id: string;
  name: string;
  description?: string;
  target?: string;
  secrets?: string[];
  rules: StatusRule[];
}
