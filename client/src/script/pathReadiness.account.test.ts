import { describe, expect, it } from "vitest";
import type { Account } from "../persistence/accountsStore";
import { pathsAvailableForAccount } from "./pathReadiness";
import type { PathDocument } from "./types";
import { SCRIPT_VERSION } from "./types";

function path(partial: Partial<PathDocument> & { id: string; inputs: string[] }): PathDocument {
  return {
    id: partial.id,
    version: SCRIPT_VERSION,
    setup: {
      name: partial.id,
      description: "",
      target: "1000",
      timeoutMs: 30_000,
      speechPreferences: { autoListen: true },
      inputs: partial.inputs,
    },
    steps: [
      {
        id: "s1",
        label: "end",
        when: "goodbye",
        then: "",
        rule: "End call",
        output: "",
      },
    ],
    conversationFlow: [],
  };
}

describe("pathsAvailableForAccount", () => {
  it("matches paths when account covers required inputs", () => {
    const account: Account = {
      id: "a1",
      name: "Test",
      fields: {
        account_pin: { kind: "secret", vaultKey: "pin" },
        ssn_last4: { kind: "plain", value: "6789" },
      },
      updatedAt: new Date().toISOString(),
    };
    const ready = path({ id: "ready", inputs: ["account_pin", "ssn_last4"] });
    const blocked = path({ id: "blocked", inputs: ["account_pin", "missing"] });
    const result = pathsAvailableForAccount(account, [ready, blocked]);
    expect(result.map((p) => p.id)).toEqual(["ready"]);
  });
});
