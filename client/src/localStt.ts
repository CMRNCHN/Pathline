/**
 * Local STT — audio/transcripts stay on device.
 * Uses Web Speech API when available; falls back to manual entry.
 */

export interface TranscriptResult {
  transcript: string;
  transcriptHash: string;
  source: "web_speech" | "manual" | "unavailable";
}

async function hashText(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getSpeechRecognition(): any | null {
  const w = window as unknown as {
    SpeechRecognition?: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

interface SpeechRecognitionInstance {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}

interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionResultList {
  length: number;
  [index: number]: { [index: number]: { transcript: string } };
}

export function isSpeechRecognitionAvailable(): boolean {
  return getSpeechRecognition() !== null;
}

export function startLocalRecognition(
  onResult: (result: TranscriptResult) => void,
  onError: (msg: string) => void
): (() => void) | null {
  const SpeechRecognition = getSpeechRecognition();
  if (!SpeechRecognition) {
    onError("Web Speech API unavailable — enter transcript manually");
    return null;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  recognition.onresult = async (event: SpeechRecognitionEvent) => {
    const transcript = event.results[0]?.[0]?.transcript?.trim() || "";
    const transcriptHash = await hashText(transcript);
    onResult({ transcript, transcriptHash, source: "web_speech" });
  };

  recognition.onerror = () => onError("Speech recognition failed");
  recognition.start();

  return () => recognition.stop();
}

/** Continuous listen — restarts on end until stopped. Phrases stay on device. */
export function startContinuousRecognition(
  onPhrase: (text: string) => void,
  onError: (msg: string) => void
): (() => void) | null {
  const SpeechRecognition = getSpeechRecognition();
  if (!SpeechRecognition) {
    onError("Web Speech API unavailable");
    return null;
  }

  let active = true;
  let recognition: SpeechRecognitionInstance | null = null;

  const start = () => {
    if (!active) return;
    const rec = new SpeechRecognition();
    recognition = rec;
    rec.continuous = true;
    rec.interimResults = false;
    rec.lang = "en-US";

    rec.onresult = (event: SpeechRecognitionEvent) => {
      for (let i = event.results.length - 1; i >= 0; i--) {
        const text = event.results[i]?.[0]?.transcript?.trim();
        if (text) {
          onPhrase(text);
          break;
        }
      }
    };

    rec.onerror = () => {
      if (active) onError("Speech recognition interrupted");
    };

    rec.onend = () => {
      if (active) start();
    };

    rec.start();
  };

  start();

  return () => {
    active = false;
    recognition?.stop();
  };
}

export async function manualTranscript(text: string): Promise<TranscriptResult> {
  const transcriptHash = await hashText(text);
  return { transcript: text, transcriptHash, source: "manual" };
}
