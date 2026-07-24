import type { PathDocument, RunState } from "../script/types";
import type { CallTransport, TransportEvent } from "../transport";
import { EventLedger, exportLedgerDigest, type CallEvent } from "../callstate";
import { hashDtmfSequence, sendDtmfSequence } from "../dtmf";
import {
  END_NOW_DETECT,
  hashCollected,
  initialRunState,
  NEXT_UTTERANCE_DETECT,
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

function dialTargetClass(target: string): "empty" | "lab-ext" | "long" {
  const digits = target.replace(/\D/g, "");
  if (!digits) return "empty";
  // Lab Asterisk extensions are short (e.g. 1000); production CLIs are longer.
  return digits.length <= 6 ? "lab-ext" : "long";
}

function sanitizeFailDetail(detail: string | undefined): string | undefined {
  if (!detail) return undefined;
  // Keep structured timeout/status copy; drop anything that looks like a long digit string.
  return detail.replace(/\d{7,}/g, "[digits]");
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
  private sawConnected = false;
  private sawAnswered = false;
  private sawError = false;
  private sawDisconnected = false;
  private dialTimeoutMs: number | null = null;

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

    const timeoutMs = Math.max(1_000, this.options.path.setup.timeoutMs || 30_000);
    this.dialTimeoutMs = timeoutMs;
    const targetClass = dialTargetClass(target);
    console.info("[pathline:run] dial", {
      sessionPrefix: this.options.sessionId.slice(0, 8),
      timeoutMs,
      targetClass,
      transport: transport.mode,
    });

    try {
      await transport.dial(target);
    } catch (error) {
      const message = asErrorMessage(error, "Dial failed");
      await this.terminate("failed", message, false);
      throw new Error(message);
    }

    let timer: number | undefined;
    try {
      await Promise.race([
        connected,
        new Promise<never>((_, reject) => {
          timer = window.setTimeout(() => {
            console.warn("[pathline:run] connect-timeout", {
              sessionPrefix: this.options.sessionId.slice(0, 8),
              timeoutMs,
              targetClass,
              sawConnected: this.sawConnected,
              sawAnswered: this.sawAnswered,
              sawError: this.sawError,
              sawDisconnected: this.sawDisconnected,
              callStarted: this.callStartedRecorded,
            });
            reject(new Error(`Call did not connect within ${timeoutMs} ms`));
          }, timeoutMs);
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
    } else if (automated && text.trim()) {
      // Open capture / open end require all prior flow Steps matched; log gating only.
      const matched = new Set(this.state.matchedFlowIds ?? []);
      const gatedOpen = path.conversationFlow.filter(
        (step, index) =>
          (step.detect === NEXT_UTTERANCE_DETECT || step.detect === END_NOW_DETECT) &&
          !matched.has(step.id) &&
          !path.conversationFlow.slice(0, index).every((prior) => matched.has(prior.id))
      );
      if (gatedOpen.length > 0) {
        console.info("[pathline:run] open-step-gated", {
          sessionPrefix: this.options.sessionId.slice(0, 8),
          phraseLength: text.trim().length,
          matchedFlowCount: matched.size,
          gatedOpenCount: gatedOpen.length,
          gatedActions: gatedOpen.map((step) => step.action),
        });
      }
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
      if (event.type === "connected") this.sawConnected = true;
      if (event.type === "answered") this.sawAnswered = true;
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
      this.sawError = true;
      const message = event.detail || "Native call transport failed";
      this.dialReject?.(new Error(message));
      await this.terminate("failed", message, false);
      return;
    }

    if (event.type === "disconnected") {
      this.sawDisconnected = true;
      await this.terminate("disconnect", event.detail || "Call disconnected", false);
    }
  }

  private failKind(
    requested: "completed" | "failed" | "abandoned" | "disconnect",
    outcome: RunLifecyclePhase,
    detail: string | undefined
  ): string {
    if (outcome === "completed") return "completed";
    if (outcome === "abandoned") return "user-abandon";
    if (requested === "disconnect") return "disconnect-incomplete";
    if (detail?.includes("did not connect within")) return "connect-timeout";
    if (this.sawError) return "transport-error";
    if (!this.callStartedRecorded) return "pre-connect-fail";
    return "failed";
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
      const matchedFlowCount = this.state.matchedFlowIds?.length ?? 0;
      const collectedKeyCount = Object.keys(this.state.collected).length;
      const failKind = this.failKind(requested, outcome, detail);
      const safeDetail = sanitizeFailDetail(detail);

      console.warn("[pathline:run] terminate", {
        sessionPrefix: this.options.sessionId.slice(0, 8),
        outcome,
        failKind,
        detail: safeDetail,
        callStarted: this.callStartedRecorded,
        matchedFlowCount,
        collectedKeyCount,
        flowCompleted: this.state.completed,
        sawConnected: this.sawConnected,
        sawAnswered: this.sawAnswered,
        sawError: this.sawError,
        sawDisconnected: this.sawDisconnected,
        dialTimeoutMs: this.dialTimeoutMs,
      });

      await this.ledger.append({
        type: "CALL_ENDED",
        metadata: {
          outcome: ledgerOutcome,
          failKind,
          callStarted: this.callStartedRecorded,
          matchedFlowCount,
          collectedKeyCount,
          sawConnected: this.sawConnected,
          sawAnswered: this.sawAnswered,
          sawError: this.sawError,
          sawDisconnected: this.sawDisconnected,
          ...(this.dialTimeoutMs != null ? { dialTimeoutMs: this.dialTimeoutMs } : {}),
          ...(safeDetail ? { detailClass: safeDetail.slice(0, 120) } : {}),
        },
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
