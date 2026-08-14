import { describe, expect, it } from "vitest";
import { groupWorkflowFamilies, workflowFamilyKey } from "./workflowFamilies";
import type { PathDocument } from "./types";

function stub(name: string, id = name): PathDocument {
  return {
    id,
    version: 2,
    setup: {
      name,
      description: "",
      target: "",
      timeoutMs: 10_000,
      speechPreferences: { autoListen: true },
      inputs: [],
    },
    steps: [],
    conversationFlow: [],
  };
}

describe("workflowFamilies", () => {
  it("strips copy suffixes into one family key", () => {
    expect(workflowFamilyKey(stub("Claim status check"))).toBe("Claim status check");
    expect(workflowFamilyKey(stub("Claim status check (copy)"))).toBe("Claim status check");
    expect(workflowFamilyKey(stub("Claim status check (copy) (copy 2)"))).toBe(
      "Claim status check"
    );
  });

  it("collapses copy stacks under one latest revision", () => {
    const families = groupWorkflowFamilies([
      stub("Claim status check", "a"),
      stub("Claim status check (copy)", "b"),
      stub("Claim status check (copy)", "c"),
      stub("", "d1"),
      stub("", "d2"),
    ]);
    expect(families).toHaveLength(2);
    const claim = families.find((f) => f.key === "Claim status check");
    expect(claim?.revisions).toHaveLength(3);
    expect(claim?.latest.id).toBe("c");
    const untitled = families.find((f) => f.key === "Untitled");
    expect(untitled?.revisions).toHaveLength(2);
  });
});
