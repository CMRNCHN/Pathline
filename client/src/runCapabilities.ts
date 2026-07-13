/**
 * Web shell capabilities — automation requires CallTransport (desktop/native client).
 * Manual phrase paste + DtmfGuide remain as fallback when transport is null.
 */
export const AUTOMATED_DTMF_REQUIRES_TRANSPORT = true;

export const voiceInputPlaceholder = "Voice input (local STT when transport active)";
