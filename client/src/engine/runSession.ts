import type { PathDocument, RunState } from "../script/types";
import type { CallTransport } from "../transport";
import { EventLedger, exportLedgerDigest, type CallEvent } from "../callstate";
import { hashDtmfSequence, sendDtmfSequence } from "../dtmf";
import {
  hashCollected,
  initialRunState,
  processPhrase,
  type ProcessPhraseResult,
} from "./runEngine";

export interface RunSessionOptions {
  path: PathDocument;
  variables: Record<string, string>;
  sessionId: string;
  transport: CallTransport | null;
}

/**
 * Orchestrates transport + runEngine + ledger.
 * Single ownership boundary — do not split call media from automation again.
 */
export class RunSession {
  private state: RunState;
  private readonly ledger: EventLedger;

  constructor(private readonly options: RunSessionOptions) {
    this.state = initialRunState();
    this.ledger = new EventLedger(options.sessionId);
  }

  getState(): RunState {
    return this.state;
  }

  getEvents(): CallEvent[] {
    return this.ledger.getEvents();
  }

  async getLedgerDigest(): Promise<string> {
    return exportLedgerDigest(this.ledger.getEvents());
  }

  async startCall(target: string): Promise<void> {
    const { transport } = this.options;
    if (!transport) return;
    await transport.dial(target);
    await this.ledger.append({ type: "CALL_STARTED", metadata: { targetLength: target.length } });
  }

  async processPhrase(text: string): Promise<ProcessPhraseResult> {
    const { path, variables, transport } = this.options;
    const automated = transport !== null;

    const result = processPhrase(text, path, variables, this.state, { automated });
    this.state = result.state;

    if (result.matched) {
      await this.ledger.append({
        type: "PHRASE_MATCHED",
        metadata: { phraseLength: text.trim().length },
      });
    }

    if (result.dtmfAction && transport) {
      const { step, sequence } = result.dtmfAction;
      await sendDtmfSequence(
        (digit, durationMs) => transport.sendDTMF(digit, durationMs),
        sequence
      );
      const hash = await hashDtmfSequence(sequence);
      await this.ledger.append({
        type: "DTMF_SENT",
        metadata: { step, digits: sequence.length, hash },
      });
      await this.ledger.append({ type: "STEP_COMPLETED", metadata: { step } });
    }

    if (result.shouldComplete) {
      await this.ledger.append({
        type: "CALL_ENDED",
        metadata: { outcome: "COMPLETED" },
      });
      if (transport) await transport.hangup();
    }

    return result;
  }

  async hangup(): Promise<void> {
    const { transport } = this.options;
    if (transport) await transport.hangup();
    await this.ledger.append({
      type: "CALL_ENDED",
      metadata: { outcome: "ABANDONED" },
    });
  }

  async finalizeCollected(): Promise<{ collectedHash: string; events: CallEvent[] }> {
    const collectedHash = await hashCollected(this.state.collected);
    return { collectedHash, events: this.ledger.getEvents() };
  }
}
