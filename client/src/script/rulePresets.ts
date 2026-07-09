export interface CapturePreset {
  id: string;
  label: string;
  triggerHint: string;
  outputVar: string;
}

export interface RespondPreset {
  id: string;
  label: string;
  triggerHint: string;
  varName: string;
}

export interface NavigateTriggerPreset {
  id: string;
  label: string;
  phrase: string;
}

export const CAPTURE_PRESETS: CapturePreset[] = [
  { id: "claim_status", label: "Claim Status", triggerHint: "Your claim status is", outputVar: "claim_status" },
  { id: "account_balance", label: "Account Balance", triggerHint: "Your balance is", outputVar: "account_balance" },
  { id: "confirmation_number", label: "Confirmation Number", triggerHint: "Your confirmation number is", outputVar: "confirmation_number" },
  { id: "reference_number", label: "Reference Number", triggerHint: "Your reference number is", outputVar: "reference_number" },
  { id: "authorization_number", label: "Authorization Number", triggerHint: "Your authorization number is", outputVar: "authorization_number" },
  { id: "member_id", label: "Member ID", triggerHint: "Your member ID is", outputVar: "member_id" },
];

export const RESPOND_PRESETS: RespondPreset[] = [
  { id: "account_number", label: "Account Number", triggerHint: "Please enter your account number", varName: "account_number" },
  { id: "member_id", label: "Member ID", triggerHint: "Enter your member ID", varName: "member_id" },
  { id: "date_of_birth", label: "Date of Birth", triggerHint: "Enter your date of birth", varName: "date_of_birth" },
  { id: "zip_code", label: "ZIP Code", triggerHint: "Enter your zip code", varName: "zip_code" },
  { id: "phone_number", label: "Phone Number", triggerHint: "Enter your phone number", varName: "phone_number" },
];

export const NAVIGATE_KEYS = ["1", "2", "3", "#", "*"] as const;
export type NavigateKey = (typeof NAVIGATE_KEYS)[number];

export const NAVIGATE_TRIGGER_PRESETS: NavigateTriggerPreset[] = [
  { id: "billing", label: "For billing", phrase: "For billing" },
  { id: "claims", label: "For claims", phrase: "For claims" },
  { id: "customer_service", label: "Customer service", phrase: "customer service" },
];

export const CUSTOM_PRESET_ID = "custom";

export function findCapturePreset(id: string): CapturePreset | undefined {
  return CAPTURE_PRESETS.find((p) => p.id === id);
}

export function findRespondPreset(id: string): RespondPreset | undefined {
  return RESPOND_PRESETS.find((p) => p.id === id);
}
