/** Field-name heuristics for display formatting. Never log or return raw secrets. */

const CC_NAME =
  /^(cc|cc_num|cc_number|credit_card|creditcard|card_number|card_num|card)$/i;

/** True when the field name looks like a credit-card number input. */
export function isCreditCardFieldName(name: string): boolean {
  return CC_NAME.test(name.trim());
}

/** Digits only — what DTMF / vault storage should use. */
export function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

/**
 * Format a digit string as ####-####-####-#### (groups of 4).
 * Accepts already-dashed input; truncates at 19 digits (Amex+padding safe).
 */
export function formatCreditCardGroups(value: string): string {
  const digits = digitsOnly(value).slice(0, 19);
  if (!digits) return "";
  return digits.replace(/(\d{4})(?=\d)/g, "$1-");
}

/** Format for display when the field name implies a card number. */
export function formatFieldDisplay(name: string, value: string): string {
  if (isCreditCardFieldName(name)) return formatCreditCardGroups(value);
  return value;
}

/** Normalize on save: CC fields store digits-only; others unchanged. */
export function normalizeFieldStorage(name: string, value: string): string {
  if (isCreditCardFieldName(name)) return digitsOnly(value);
  return value;
}
