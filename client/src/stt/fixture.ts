/**
 * Deterministic, headless proof of the on-device STT pipeline.
 *
 * Drives a known PCM buffer through the exact production path —
 *   FixtureTransport.onAudio → AudioSession → LocalWhisperEngine (VAD /
 *   endpointing) → mock on-device backend → runSession.processPhrase →
 *   DTMF injection via transport
 * — using the real `lab-account-status` Path. No microphone, no network, and no
 * bundled Whisper model required; the backend is a local mock that returns
 * scripted transcripts, standing in for whisper.cpp on the desktop host.
 *
 * Run it with: `npm run stt:fixture` (see client/scripts/run-stt-fixture.mjs).
 */
import { normalizeScript } from "../script/compile";
import { RunSession } from "../engine/runSession";
import { AudioSession } from "../transport/AudioSession";
import { PREFERRED_STT_SAMPLE_RATE } from "../transport/audioFormat";
import type {
  AudioFrameHandler,
  CallTransport,
  TransportEventHandler,
} from "../transport/CallTransport";
import { createSttEngine } from "./index";
import { LocalWhisperEngine } from "./whisperEngine";
import type { WhisperBackend } from "./whisperEngine";

/** In-memory transport: drives onAudio frames and records injected DTMF. */
class FixtureTransport implements CallTransport {
  readonly mode = "simulator" as const;
  readonly dtmfDigits: string[] = [];
  private audioHandlers = new Set<AudioFrameHandler>();

  async getReadiness() {
    return { ready: true, mode: this.mode, label: "STT fixture" } as const;
  }
  async dial(): Promise<void> {}
  async answer(): Promise<void> {}
  async sendDTMF(digits: string): Promise<void> {
    this.dtmfDigits.push(digits);
  }
  async hangup(): Promise<void> {}

  onAudio(handler: AudioFrameHandler): () => void {
    this.audioHandlers.add(handler);
    return () => this.audioHandlers.delete(handler);
  }
  onEvent(_handler: TransportEventHandler): () => void {
    void _handler;
    return () => {};
  }

  /** Push one PCM frame to every subscribed recognizer (like the SIP bridge). */
  emitAudio(pcm: Float32Array, sampleRate: number): void {
    for (const handler of this.audioHandlers) handler(pcm, sampleRate);
  }
}

/** Raw `lab-account-status` Path (mirrors client/public/scripts). */
const LAB_SCRIPT = {
  id: "lab-account-status",
  version: 2,
  setup: {
    name: "Lab account status (Asterisk 1000)",
    description: "Fixture copy of the lab IVR Path.",
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

/** One synthetic utterance: energetic speech followed by endpointing silence. */
function utteranceFrames(sampleRate: number): { speech: Float32Array; silence: Float32Array } {
  const speech = new Float32Array(Math.round(sampleRate * 0.3)).fill(0.2); // 300ms tone
  const silence = new Float32Array(Math.round(sampleRate * 0.7)).fill(0); // 700ms gap
  return { speech, silence };
}

export interface FixtureResult {
  ok: boolean;
  phrases: string[];
  dtmf: string;
  collected: Record<string, string>;
  completed: boolean;
  transcriptLeakInLedger: boolean;
  checks: Record<string, boolean>;
}

export async function runPipelineFixture(): Promise<FixtureResult> {
  const sampleRate = PREFERRED_STT_SAMPLE_RATE;
  const path = normalizeScript(LAB_SCRIPT);

  const transport = new FixtureTransport();
  const runSession = new RunSession({
    path,
    variables: { account_pin: "1234", ssn_last4: "6789" },
    sessionId: "fixture-session",
    transport,
  });
  const audioSession = new AudioSession(transport);

  // Scripted transcripts the "on-device model" would return per utterance.
  // Chosen so each maps unambiguously to one Path step.
  const scripted = [
    "please press 1 for account", // -> main_menu, DTMF "1"
    "now enter your pin followed by pound", // -> pin_entry, DTMF "1234#"
    "the code 1234", // -> read_status, capture account_balance
    "thank you and goodbye", // -> end_call, completes the run
  ];

  let next = 0;
  const backend: WhisperBackend = {
    async transcribe() {
      return scripted[next++] ?? "";
    },
  };

  const engine = new LocalWhisperEngine(backend, { minUtteranceMs: 200, endpointSilenceMs: 600 });

  const phrases: string[] = [];
  const pending: Promise<unknown>[] = [];
  const stop = audioSession.runStt(engine, (phrase) => {
    phrases.push(phrase);
    pending.push(runSession.processPhrase(phrase));
  });

  const { speech, silence } = utteranceFrames(sampleRate);
  for (let i = 0; i < scripted.length; i++) {
    transport.emitAudio(speech, sampleRate);
    transport.emitAudio(silence, sampleRate);
  }

  await engine.whenIdle();
  await Promise.all(pending);
  stop();

  const state = runSession.getState();
  const dtmf = transport.dtmfDigits.join("");
  const events = runSession.getEvents();
  const ledgerJson = JSON.stringify(events);
  // Privacy: no transcript text may appear in the audit ledger.
  const transcriptLeakInLedger = scripted.some((p) => ledgerJson.includes(p));

  const checks = {
    fourPhrasesTranscribed: phrases.length === 4,
    mainMenuAndPinDtmf: dtmf === "11234#",
    balanceCaptured: state.collected.account_balance === "the code 1234",
    runCompleted: state.completed === true,
    noTranscriptInLedger: !transcriptLeakInLedger,
  };

  const ok = Object.values(checks).every(Boolean);

  return {
    ok,
    phrases,
    dtmf,
    collected: state.collected,
    completed: state.completed,
    transcriptLeakInLedger,
    checks,
  };
}

/** Mutable view of the browser globals `createSttEngine` probes. */
interface SttGlobals {
  __pathlineWhisper?: unknown;
  __pathlineSipBridge?: unknown;
  SpeechRecognition?: unknown;
  webkitSpeechRecognition?: unknown;
}

export interface SelectionFixtureResult {
  ok: boolean;
  cases: { name: string; source: string | null; expected: string | null; pass: boolean }[];
}

/**
 * Proves engine selection — most importantly that a bridge-backed automated run
 * NEVER selects Web Speech, even when the Web Speech API is available.
 */
export function runSelectionFixture(): SelectionFixtureResult {
  const g = globalThis as unknown as SttGlobals;
  const saved: SttGlobals = {
    __pathlineWhisper: g.__pathlineWhisper,
    __pathlineSipBridge: g.__pathlineSipBridge,
    SpeechRecognition: g.SpeechRecognition,
    webkitSpeechRecognition: g.webkitSpeechRecognition,
  };

  const fakeWhisper = { transcribe: async () => "" };
  const fakeBridge = {};
  const FakeSpeech = function FakeSpeech() {} as unknown;

  const reset = () => {
    delete g.__pathlineWhisper;
    delete g.__pathlineSipBridge;
    delete g.SpeechRecognition;
    delete g.webkitSpeechRecognition;
  };

  const select = (
    env: Partial<SttGlobals>,
    automated: boolean
  ): string | null => {
    reset();
    Object.assign(g, env);
    return createSttEngine({ automated }).engine?.source ?? null;
  };

  const cases: SelectionFixtureResult["cases"] = [];
  const record = (name: string, source: string | null, expected: string | null) =>
    cases.push({ name, source, expected, pass: source === expected });

  try {
    record(
      "automated + bridge + whisper -> local_whisper",
      select({ __pathlineSipBridge: fakeBridge, __pathlineWhisper: fakeWhisper }, true),
      "local_whisper"
    );
    record(
      "automated + bridge + NO whisper (web speech present) -> null (guard)",
      select({ __pathlineSipBridge: fakeBridge, SpeechRecognition: FakeSpeech }, true),
      null
    );
    record(
      "automated + no bridge + web speech -> web_speech (dev)",
      select({ SpeechRecognition: FakeSpeech }, true),
      "web_speech"
    );
    record(
      "manual + web speech -> web_speech",
      select({ SpeechRecognition: FakeSpeech }, false),
      "web_speech"
    );
  } finally {
    reset();
    Object.assign(g, saved);
  }

  return { ok: cases.every((c) => c.pass), cases };
}
