import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CallStateBoard } from "@/components/CallStateBoard";
import { DtmfGuide } from "@/components/DtmfGuide";
import {
  callFromSession,
  pathFromScript,
  projectLiveStatus,
  runLogToCallEvents,
} from "@/callstate";
import type { CallEvent } from "@/callstate";
import type { RunSession } from "@/engine/runSession";
import { isSpeechRecognitionAvailable } from "@/localStt";
import { createSttEngine } from "@/stt";
import { AudioSession } from "@/transport/AudioSession";
import { createAppTransport } from "@/transport/createAppTransport";
import type { RunState } from "@/script/runEngine";
import type { Path } from "@/script/types";
import { scriptDisplayName } from "@/script/storage";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

interface RunActivePanelProps {
  runSession: RunSession;
  script: Path;
  sessionId: string;
  automated: boolean;
  onCallStateCaptured: (
    collected: Record<string, string>,
    collectedHash: string,
    callEvents: CallEvent[]
  ) => void;
}

export function RunActivePanel({
  runSession,
  script,
  sessionId,
  automated,
  onCallStateCaptured,
}: RunActivePanelProps) {
  const [run, setRun] = useState<RunState>(() => runSession.getState());
  const [ledgerEvents, setLedgerEvents] = useState<CallEvent[]>(() => runSession.getEvents());
  const [ivrText, setIvrText] = useState("");
  const path = pathFromScript(script);
  const callEvents = runLogToCallEvents(run.log, path);
  const mergedEvents = [...ledgerEvents, ...callEvents];
  const call = callFromSession(sessionId, "local-client", path.id, mergedEvents);
  const liveStatus = projectLiveStatus(call, path);
  const [autoListen, setAutoListen] = useState(script.setup.speechPreferences.autoListen);
  const [listenError, setListenError] = useState<string | null>(null);
  const debounceRef = useRef<number | undefined>(undefined);

  // Reuse the app transport so onAudio subscribes to the same SIP bridge that
  // RunSession injects DTMF through. Null in web-only manual mode.
  const transport = useMemo(() => createAppTransport(), []);
  const audioSession = useMemo(
    () => (transport ? new AudioSession(transport) : null),
    [transport]
  );
  const listenSupported = automated || isSpeechRecognitionAvailable();

  const syncFromSession = useCallback(() => {
    setRun(runSession.getState());
    setLedgerEvents(runSession.getEvents());
  }, [runSession]);

  const applyPhraseNow = useCallback(
    async (text: string) => {
      const result = await runSession.processPhrase(text);
      syncFromSession();

      if (result.shouldComplete) {
        const state = runSession.getState();
        const { collectedHash, events } = await runSession.finalizeCollected();
        onCallStateCaptured(state.collected, collectedHash, events);
      }
    },
    [runSession, syncFromSession, onCallStateCaptured]
  );

  const applyPhraseDebounced = useCallback(
    (text: string) => {
      window.clearTimeout(debounceRef.current);
      debounceRef.current = window.setTimeout(() => {
        void applyPhraseNow(text);
      }, 150);
    },
    [applyPhraseNow]
  );

  useEffect(() => {
    if (!autoListen || run.completed) return;

    setListenError(null);

    // Picks on-device Whisper when available; never Web Speech for a
    // bridge-backed automated run (returns engine: null with a reason instead).
    const { engine, unavailableReason } = createSttEngine({ automated });
    if (!engine) {
      setAutoListen(false);
      setListenError(unavailableReason ?? "Listening unavailable — paste phrases manually.");
      return;
    }

    // Bridge-backed runs: feed transport onAudio PCM into the engine.
    // Web Speech (browser dev) captures its own mic, so it starts standalone.
    if (audioSession && engine.source !== "web_speech") {
      return audioSession.runStt(engine, applyPhraseDebounced, (msg) => setListenError(msg));
    }

    engine.start(applyPhraseDebounced, (msg) => setListenError(msg));
    return () => engine.stop();
  }, [autoListen, run.completed, applyPhraseDebounced, automated, audioSession]);

  const handleManualMatch = () => {
    if (!ivrText.trim()) return;
    void applyPhraseNow(ivrText.trim());
    setIvrText("");
  };

  const dismissDtmf = () => {
    setRun((prev) => ({ ...prev, pendingDtmf: undefined, pendingTrigger: undefined }));
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
        <CardTitle>{scriptDisplayName(script)}</CardTitle>
        {listenSupported && !run.completed && (
          <Button
            type="button"
            size="sm"
            variant={autoListen ? "default" : "outline"}
            onClick={() => setAutoListen((v) => !v)}
          >
            {autoListen ? "● Listening" : "Auto-listen"}
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {!automated && (
          <Alert>
            <AlertTitle>Manual mode</AlertTitle>
            <AlertDescription>
              Automated calls require the Pathline desktop app. Paste IVR phrases below and press
              the keys on your phone when prompted.
            </AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="steps">
          <TabsList>
            <TabsTrigger value="steps">Steps</TabsTrigger>
            <TabsTrigger value="audit">Audit</TabsTrigger>
            <TabsTrigger value="dtmf">Keys</TabsTrigger>
          </TabsList>

          <TabsContent value="steps" className="space-y-4 pt-4">
            <p className="text-sm text-muted-foreground">
              {automated
                ? autoListen
                  ? "Listening locally — IVR phrases match and keys are pressed automatically."
                  : "Paste what you hear, or enable auto-listen. Keys are pressed automatically."
                : autoListen
                  ? "Listening locally — paste or speak IVR phrases to match your Workflow."
                  : "Paste what you hear, or enable auto-listen."}
            </p>

            {listenError && (
              <Alert variant="destructive">
                <AlertTitle>Listen error</AlertTitle>
                <AlertDescription>{listenError}</AlertDescription>
              </Alert>
            )}

            {!run.completed && (
              <>
                <div className="space-y-2">
                  <label htmlFor="ivr-phrase" className="text-sm font-medium">
                    Listen
                  </label>
                  <Textarea
                    id="ivr-phrase"
                    rows={2}
                    value={ivrText}
                    onChange={(e) => setIvrText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleManualMatch();
                      }
                    }}
                  />
                </div>
                <Button
                  type="button"
                  className="w-full"
                  onClick={handleManualMatch}
                  disabled={!ivrText.trim()}
                >
                  Match
                </Button>
              </>
            )}

            {Object.keys(run.collected).length > 0 && (
              <div className="space-y-2">
                <h5 className="text-sm font-medium">Captured</h5>
                <pre className="rounded-lg bg-muted p-3 text-xs font-mono overflow-x-auto">
                  {JSON.stringify(run.collected, null, 2)}
                </pre>
              </div>
            )}

            {run.completed && (
              <Alert>
                <AlertTitle>Complete</AlertTitle>
                <AlertDescription>Run complete — encrypted callstate submitted.</AlertDescription>
              </Alert>
            )}
          </TabsContent>

          <TabsContent value="audit" className="pt-4">
            <CallStateBoard liveStatus={liveStatus} path={path} label="Live callstate" />
            {run.log.length > 0 && (
              <ScrollArea className="mt-4 h-48 rounded-lg border p-3">
                <ul className="space-y-1 text-xs font-mono">
                  {run.log.map((entry, i) => (
                    <li key={i}>{entry.message}</li>
                  ))}
                </ul>
              </ScrollArea>
            )}
          </TabsContent>

          <TabsContent value="dtmf" className="pt-4">
            {automated ? (
              <p className="text-sm text-muted-foreground">
                Key sequences are sent automatically when phrases match.
              </p>
            ) : run.pendingDtmf ? (
              <DtmfGuide
                sequence={run.pendingDtmf}
                trigger={run.pendingTrigger}
                onComplete={dismissDtmf}
              />
            ) : (
              <p className="text-sm text-muted-foreground">No pending key sequence.</p>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
