import type { CallEvent, CallEventType } from "./types";

export interface LedgerAppendInput {
  type: CallEventType;
  metadata?: Record<string, unknown>;
}

export async function sha256Hex(payload: string): Promise<string> {
  return sha256Bytes(new TextEncoder().encode(payload));
}

export async function sha256Bytes(data: Uint8Array): Promise<string> {
  const copy = new Uint8Array(data);
  const hash = await crypto.subtle.digest("SHA-256", copy);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Chain fields written by EventLedger. Input metadata (including DTMF `hash`) is preserved. */
export const LEDGER_PREV_HASH_KEY = "prevHash";
export const LEDGER_CHAIN_HASH_KEY = "chainHash";
/** Legacy chain field; older events overwrote DTMF `hash` with this. */
export const LEDGER_LEGACY_CHAIN_HASH_KEY = "hash";

export function eventInputMetadata(metadata?: Record<string, unknown>): Record<string, unknown> {
  if (!metadata) return {};
  const rest: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(metadata)) {
    if (key === LEDGER_PREV_HASH_KEY || key === LEDGER_CHAIN_HASH_KEY) continue;
    rest[key] = value;
  }
  return rest;
}

export function eventPrevHash(metadata?: Record<string, unknown>): string {
  return typeof metadata?.[LEDGER_PREV_HASH_KEY] === "string" ? metadata[LEDGER_PREV_HASH_KEY] : "";
}

export function eventChainHash(metadata?: Record<string, unknown>): string | undefined {
  if (typeof metadata?.[LEDGER_CHAIN_HASH_KEY] === "string") {
    return metadata[LEDGER_CHAIN_HASH_KEY];
  }
  if (
    typeof metadata?.[LEDGER_LEGACY_CHAIN_HASH_KEY] === "string" &&
    metadata[LEDGER_CHAIN_HASH_KEY] === undefined
  ) {
    return metadata[LEDGER_LEGACY_CHAIN_HASH_KEY];
  }
  return undefined;
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
    const chainHash = await sha256Hex(body);
    const event: CallEvent = {
      id: crypto.randomUUID(),
      timestamp,
      type: input.type,
      metadata: {
        ...input.metadata,
        [LEDGER_PREV_HASH_KEY]: this.lastHash,
        [LEDGER_CHAIN_HASH_KEY]: chainHash,
      },
    };
    this.events.push(event);
    this.lastHash = chainHash;
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
  const canonical = JSON.stringify(
    events.map((e) => ({ id: e.id, type: e.type, timestamp: e.timestamp, metadata: e.metadata }))
  );
  return sha256Hex(canonical);
}
