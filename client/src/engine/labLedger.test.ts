import { describe, expect, it } from "vitest";
import { inspectRun } from "../audit";
import { pathSnapshotFromScript, definedStepsFromSnapshot } from "../callstate";
import { normalizeScript } from "../script/compile";
import { RunSession } from "./runSession";
import type { CallTransport, TransportEventHandler } from "../transport/CallTransport";

(globalThis as { window?: typeof globalThis }).window = globalThis;

/** In-memory transport so DTMF injection records on the ledger. */
class LabTransport implements CallTransport {
  readonly mode = "simulator" as const;
  readonly dtmfDigits: string[] = [];

  async getReadiness() {
    return { ready: true, mode: this.mode, label: "lab ledger" } as const;
  }
  async dial(): Promise<void> {}
  async answer(): Promise<void> {}
  async sendDTMF(digits: string): Promise<void> {
    this.dtmfDigits.push(digits);
  }
  async hangup(): Promise<void> {}
  onAudio(): () => void {
    return () => {};
  }
  onEvent(_handler: TransportEventHandler): () => void {
    void _handler;
    return () => {};
  }
}

const LAB_SCRIPT = {
  id: "lab-account-status",
  version: 2,
  setup: {
    name: "Lab account status (Asterisk 1000)",
    description: "",
    target: "1000",
    timeoutMs: 30000,
    speechPreferences: { autoListen: true },
    runtimeVariables: ["account_pin", "ssn_last4"],
  },
  ivrRules: [
    { id: "rule-main-menu", label: "main_menu", trigger: "account|press 1 for account|option 1", response: "1", rule: "Inject DTMF after detect", output: "" },
    { id: "rule-touch-tone", label: "touch_tone", trigger: "touch tone|touchtone|press 9|keypad", response: "9", rule: "Inject DTMF after detect", output: "" },
    { id: "rule-pin", label: "pin_entry", trigger: "pin|personal identification|enter your pin", response: "{{account_pin}}#", rule: "Inject DTMF after detect", output: "" },
    { id: "rule-ssn", label: "ssn_entry", trigger: "last four|social security|last four of your social", response: "{{ssn_last4}}#", rule: "Inject DTMF after detect", output: "" },
    { id: "rule-status-menu", label: "status_menu", trigger: "balance|press 1 for balance|hear your balance", response: "1", rule: "Inject DTMF after detect", output: "" },
    { id: "rule-capture", label: "read_status", trigger: "your balance|your dollars|1234|current balance", response: "", rule: "Capture value after detect", output: "account_balance" },
    { id: "rule-end", label: "end_call", trigger: "", response: "", rule: "End call", output: "" },
  ],
  conversationFlow: [],
};

describe("lab Path ledger (engine chain)", () => {
  it("records extract/end STEP_COMPLETED and cites skipped steps on an event", async () => {
    const path = normalizeScript(LAB_SCRIPT);
    const transport = new LabTransport();
    const session = new RunSession({
      path,
      variables: { account_pin: "1234", ssn_last4: "6789" },
      sessionId: "lab-ledger",
      transport,
    });

    await session.processPhrase("please press 1 for account");
    await session.processPhrase("now enter your pin followed by pound");
    await session.processPhrase("the code 1234");
    await session.processPhrase("thank you and goodbye");
    await new Promise((resolve) => setTimeout(resolve, 50));

    const events = session.getEvents();
    const types = events.map((event) => `${event.type}:${String(event.metadata?.step ?? "")}`);
    expect(types).toContain("STEP_COMPLETED:read_status");
    expect(types).toContain("STEP_COMPLETED:end_call");
    expect(JSON.stringify(events)).not.toContain("the code 1234");

    const snapshot = pathSnapshotFromScript(path);
    const report = await inspectRun({
      runId: "lab-ledger",
      pathId: path.id,
      pathName: path.setup.name,
      outcome: "completed",
      startedAt: events[0]?.timestamp ?? "",
      completedAt: events[events.length - 1]?.timestamp ?? "",
      captured: session.getState().collected,
      ledgerEvents: events,
      definedSteps: definedStepsFromSnapshot(snapshot),
      pathSnapshot: snapshot,
    });

    const skipped = report.anomalies.find((anomaly) => anomaly.code === "STEP_SKIPPED");
    expect(skipped?.explanation).toMatch(/ssn_entry|touch_tone|status_menu/);
    expect(skipped?.references.some((ref) => ref.kind === "event")).toBe(true);
    expect(report.path.pathSnapshot?.steps.some((step) => step.label === "ssn_entry")).toBe(true);
  });
});
