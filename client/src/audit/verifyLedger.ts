import {
  eventChainHash,
  eventInputMetadata,
  eventPrevHash,
  LEDGER_CHAIN_HASH_KEY,
  LEDGER_LEGACY_CHAIN_HASH_KEY,
  sha256Hex,
  type CallEvent,
} from "../callstate";
import type { LedgerVerification } from "./types";

function inputMetadataForVerify(metadata?: Record<string, unknown>): Record<string, unknown> {
  const rest = eventInputMetadata(metadata);
  if (typeof metadata?.[LEDGER_CHAIN_HASH_KEY] === "string") {
    return rest;
  }
  const legacy: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(rest)) {
    if (key === LEDGER_LEGACY_CHAIN_HASH_KEY) continue;
    legacy[key] = value;
  }
  return legacy;
}

/** Recompute the SHA-256 chain. `callId` is the Run session id used at append time. */
export async function verifyLedger(callId: string, events: CallEvent[]): Promise<LedgerVerification> {
  if (events.length === 0) {
    return { ok: true, eventCount: 0, reason: "empty" };
  }

  let prevHash = "";
  for (let index = 0; index < events.length; index++) {
    const event = events[index];
    const storedPrev = eventPrevHash(event.metadata);
    if (storedPrev !== prevHash) {
      return {
        ok: false,
        eventCount: events.length,
        breakIndex: index,
        expectedHash: prevHash,
        actualHash: storedPrev,
        reason: "prevHash mismatch",
      };
    }

    const body = JSON.stringify({
      callId,
      prevHash,
      type: event.type,
      timestamp: event.timestamp,
      metadata: inputMetadataForVerify(event.metadata),
    });
    const expected = await sha256Hex(body);
    const actual = eventChainHash(event.metadata);
    if (actual !== expected) {
      return {
        ok: false,
        eventCount: events.length,
        breakIndex: index,
        expectedHash: expected,
        actualHash: actual,
        reason: "chain hash mismatch",
      };
    }
    prevHash = expected;
  }

  return { ok: true, eventCount: events.length };
}
