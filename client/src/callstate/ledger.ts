import type { CallEvent, CallEventType } from "./types";

export interface LedgerAppendInput {
  type: CallEventType;
  metadata?: Record<string, unknown>;
}

async function sha256(payload: string): Promise<string> {
  const data = new TextEncoder().encode(payload);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Append-only event ledger with hash chain for verifiable execution history. */
export class EventLedger {
  private events: CallEvent[] = [];
  private lastHash = "";

  constructor(private readonly callId: string) {}

  async append(input: LedgerAppendInput): Promise<CallEvent> {
    const timestamp = new Date().toISOString();
    const body = JSON.stringify({
      callId: this.callId,
      prevHash: this.lastHash,
      type: input.type,
      timestamp,
      metadata: input.metadata ?? {},
    });
    const hash = await sha256(body);
    const event: CallEvent = {
      id: crypto.randomUUID(),
      timestamp,
      type: input.type,
      metadata: { ...input.metadata, prevHash: this.lastHash, hash },
    };
    this.events.push(event);
    this.lastHash = hash;
    return event;
  }

  getEvents(): CallEvent[] {
    return [...this.events];
  }

  getHeadHash(): string {
    return this.lastHash;
  }
}

export async function exportLedgerDigest(events: CallEvent[]): Promise<string> {
  const canonical = JSON.stringify(events.map((e) => ({ id: e.id, type: e.type, timestamp: e.timestamp, metadata: e.metadata })));
  return sha256(canonical);
}
