import { describe, expect, it } from "vitest";
import { compileDetect, evaluateDetect, similarTo } from "./index";

describe("evaluateDetect", () => {
  it("keeps legacy pipe-OR contains behavior", () => {
    expect(evaluateDetect("press 1 for billing", "billing|repair")).toBe(true);
    expect(evaluateDetect("press 1 for billing", "repair|claims")).toBe(false);
  });

  it("supports fuzzy substring detect strings", () => {
    expect(
      evaluateDetect(
        "prefix please enter your account suffix",
        "~please enter your account"
      )
    ).toBe(true);
  });

  it("distinguishes full-string similarTo from containsSimilarTo", () => {
    const transcript = "prefix you entered suffix";
    expect(similarTo("you entered")(transcript)).toBe(false);
    expect(compileDetect("~you entered")(transcript)).toBe(true);
  });

  it("supports regex detect strings", () => {
    expect(evaluateDetect("account 1234 confirmed", "regex:/account \\d+/")).toBe(
      true
    );
  });

  it("supports nested structured JSON and/or detect strings", () => {
    const detect = JSON.stringify({
      and: [
        "account",
        {
          or: ["balance", { regex: "status (ready|available)", flags: "i" }],
        },
      ],
    });

    expect(evaluateDetect("your account status ready", detect)).toBe(true);
    expect(evaluateDetect("your account is closed", detect)).toBe(false);
  });
});
