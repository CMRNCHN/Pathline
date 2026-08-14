import { describe, expect, it } from "vitest";
import {
  formatCreditCardGroups,
  formatFieldDisplay,
  isCreditCardFieldName,
  normalizeFieldStorage,
} from "./formatFieldValue";

describe("credit card field formatting", () => {
  it("detects common CC field names", () => {
    expect(isCreditCardFieldName("cc_num")).toBe(true);
    expect(isCreditCardFieldName("credit_card")).toBe(true);
    expect(isCreditCardFieldName("card_number")).toBe(true);
    expect(isCreditCardFieldName("account_pin")).toBe(false);
  });

  it("groups digits as ####-####-####-####", () => {
    expect(formatCreditCardGroups("4111111111111111")).toBe("4111-1111-1111-1111");
    expect(formatCreditCardGroups("4111-1111")).toBe("4111-1111");
    expect(formatCreditCardGroups("4111abcd1111")).toBe("4111-1111");
  });

  it("stores digits only for CC fields", () => {
    expect(normalizeFieldStorage("cc_num", "4111-1111-1111-1111")).toBe("4111111111111111");
    expect(normalizeFieldStorage("zip", "10001-1234")).toBe("10001-1234");
  });

  it("formats display only for CC names", () => {
    expect(formatFieldDisplay("cc", "4111111111111111")).toBe("4111-1111-1111-1111");
    expect(formatFieldDisplay("notes", "4111111111111111")).toBe("4111111111111111");
  });
});
