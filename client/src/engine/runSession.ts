import type { PathDocument, RunState } from "../script/types";
import type { CallTransport, TransportEvent } from "../transport";
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

export type RunLifecyclePhase =
  | "connecting"
  | "active"
  | "failed"
  | "completed"
  | "abandoned";

export interface RunLifecycle {
  phase: RunLifecyclePhase;
  detail?: string;
}

type LifecycleHandler = (lifecycle: RunLifecycle) => void;

function asErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

/**
 * Orchestrates transport + runEngine + ledger.
 * Single ownership boundary — do not split call media from automation again.
 */
export class RunSession {
  private state: RunState;
  private readonly ledger: EventLedger;
  private lifecycle: RunLifecycle = { phase: "connecting" };
  private readonly lifecycleHandlers = new Set<LifecycleHandler>();
  private readonly unsubscribeTransport?: () => void;
  private beforeFinalize?: () => Promise<void>;
  private eventQueue: Promise<void> = Promise.resolve();
  private terminalPromise: Promise<void> | null = null;
  private dialResolve?: () => void;
  private dialReject?: (error: Error) => void;
  private callStartedRecorded = false;

  constructor(private readonly options: RunSessionOptions) {
    this.state = initialRunState();
    this.ledger = new EventLedger(options.sessionId);
    this.unsubscribeTransport = options.transport?.onEvent((event) => {
      this.eventQueue = this.eventQueue.then(() => this.handleTransportEvent(event));
    });
  }

  getState(): RunState {
    return this.state;
  }

  getEvents(): CallEvent[] {
    return this.ledger.getEvents();
  }

  getTransport(): CallTransport | null {
    return this.options.transport;
  }

  getLifecycle(): RunLifecycle {
    return { ...this.lifecycle };
  }

  onLifecycle(handler: LifecycleHandler): () => void {
    this.lifecycleHandlers.add(handler);
    handler(this.getLifecycle());
    return () => this.lifecycleHandlers.delete(handler);
  }

  setBeforeFinalize(handler: (() => Promise<void>) | undefined): void {
    this.beforeFinalize = handler;
  }

  async getLedgerDigest(): Promise<string> {
    return exportLedgerDigest(this.ledger.getEvents());
  }

  async startCall(target: string): Promise<void> {
    const { transport } = this.options;
    if (!transport) return;

    this.setLifecycle({ phase: "connecting" });
    const readiness = await transport.getReadiness();
    if (!readiness.ready) {
      const reason = readiness.reason ?? "Automated calling is unavailable.";
      await this.terminate("failed", reason, false);
      throw new Error(reason);
    }
    if (
      this.options.path.steps.some((step) => step.rule === "Inject speech after detect") &&
      !transport.speak
    ) {
      const reason = "This Workflow contains speech Steps, but the native transport cannot speak.";
      await this.terminate("failed", reason, false);
      throw new Error(reason);
    }

    const connected = new Promise<void>((resolve, reject) => {
      this.dialResolve = resolve;
      this.dialReject = reject;
    });

    try {
      await transport.dial(target);
    } catch (error) {
      const message = asErrorMessage(error, "Dial failed");
      await this.terminate("failed", message, false);
      throw new Error(message);
    }

    const timeoutMs = Math.max(1_000, this.options.path.setup.timeoutMs || 30_000);
    let timer: number | undefined;
    try {
      await Promise.race([
        connected,
        new Promise<never>((_, reject) => {
          timer = window.setTimeout(
            () => reject(new Error(`Call did not connect within ${timeoutMs} ms`)),
            timeoutMs
          );
        }),
      ]);
    } catch (error) {
      const message = asErrorMessage(error, "Call failed before connecting");
      await this.terminate("failed", message, true);
      throw new Error(message);
    } finally {
      window.clearTimeout(timer);
      this.dialResolve = undefined;
      this.dialReject = undefined;
    }
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
      try {
        await sendDtmfSequence(
          (digit, durationMs) => transport.sendDTMF(digit, durationMs),
          sequence
        );
      } catch (error) {
        const message = asErrorMessage(error, "Keypad injection failed");
        this.scheduleTerminalFailure(message);
        throw new Error(message);
      }
      const hash = await hashDtmfSequence(sequence);
      await this.ledger.append({
        type: "DTMF_SENT",
        metadata: { step, digits: sequence.length, hash },
      });
      await this.ledger.append({ type: "STEP_COMPLETED", metadata: { step } });
    }

    if (result.speechAction && transport) {
      const { step, text } = result.speechAction;
      if (!transport.speak) {
        const message = "This transport cannot execute speech Steps.";
        this.scheduleTerminalFailure(message);
        throw new Error(message);
      }
      try {
        await transport.speak(text);
      } catch (error) {
        const message = asErrorMessage(error, "Speech injection failed");
        this.scheduleTerminalFailure(message);
        throw new Error(message);
      }
      await this.ledger.append({ type: "STEP_COMPLETED", metadata: { step } });
    }

    if (result.shouldComplete) {
      // A transport disconnect may already be flushing final STT. In that
      // case the disconnect finalizer observes state.completed after this
      // phrase returns and chooses COMPLETED without creating a second end.
      if (!this.terminalPromise) {
        // Defer finalization until the current phrase promise leaves the STT
        // queue. The finalizer itself waits for that queue, so awaiting it here
        // would make the final phrase wait on itself.
        globalThis.setTimeout(() => {
          void this.terminate("completed", undefined, true);
        }, 0);
      }
    }

    return result;
  }

  async hangup(): Promise<void> {
    await this.terminate("abandoned", "Ended by user", true);
  }

  async finalizeCollected(): Promise<{ collectedHash: string; events: CallEvent[] }> {
    const collectedHash = await hashCollected(this.state.collected);
    return { collectedHash, events: this.ledger.getEvents() };
  }

  dispose(): void {
    this.unsubscribeTransport?.();
    this.lifecycleHandlers.clear();
  }

  private setLifecycle(lifecycle: RunLifecycle): void {
    this.lifecycle = lifecycle;
    for (const handler of this.lifecycleHandlers) handler(this.getLifecycle());
  }

  private scheduleTerminalFailure(message: string): void {
    globalThis.setTimeout(() => {
      void this.terminate("failed", message, true);
    }, 0);
  }

  private async handleTransportEvent(event: TransportEvent): Promise<void> {
    if (this.terminalPromise) return;

    if (event.type === "connected" || event.type === "answered") {
      if (!this.callStartedRecorded) {
        this.callStartedRecorded = true;
        await this.ledger.append({
          type: "CALL_STARTED",
          metadata: { transport: this.options.transport?.mode ?? "manual" },
        });
      }
      this.setLifecycle({ phase: "active" });
      this.dialResolve?.();
      return;
    }

    if (event.type === "error") {
      const message = event.detail || "Native call transport failed";
      this.dialReject?.(new Error(message));
      await this.terminate("failed", message, false);
      return;
    }

    if (event.type === "disconnected") {
      await this.terminate("disconnect", event.detail || "Call disconnected", false);
    }
  }

  private async terminate(
    requested: "completed" | "failed" | "abandoned" | "disconnect",
    detail: string | undefined,
    hangup: boolean
  ): Promise<void> {
    if (this.terminalPromise) return this.terminalPromise;

    this.terminalPromise = (async () => {
      await this.beforeFinalize?.();

      const outcome =
        requested === "disconnect"
          ? this.state.completed
            ? "completed"
            : "failed"
          : requested;
      const ledgerOutcome = outcome.toUpperCase() as "COMPLETED" | "FAILED" | "ABANDONED";

      await this.ledger.append({
        type: "CALL_ENDED",
        metadata: { outcome: ledgerOutcome },
      });

      if (hangup && this.options.transport) {
        try {
          await this.options.transport.hangup();
        } catch {
          // The terminal outcome is already fixed; hangup is best-effort here.
        }
      }

      this.setLifecycle({ phase: outcome, detail });
    })();

    return this.terminalPromise;
  }
}
