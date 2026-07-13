import { useCallback, useEffect, useRef, useState } from "react";
import { CallStateBoard } from "@/components/CallStateBoard";
import { DtmfGuide } from "@/components/DtmfGuide";
import {
  callFromSession,
  newCallEvent,
  pathFromScript,
  projectLiveStatus,
  runLogToCallEvents,
} from "@/callstate";
import { isSpeechRecognitionAvailable, startContinuousRecognition } from "@/localStt";
import {
  hashCollected,
  initialRunState,
  processPhrase,
  type RunState,
} from "@/script/runEngine";
import type { Path } from "@/script/types";
import { scriptDisplayName } from "@/script/storage";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";

interface RunActivePanelProps {
  script: Path;
  variables: Record<string, string>;
  sessionId: string;
  onCallStateCaptured: (
    collected: Record<string, string>,
    transcriptHash: string,
    callEvents: ReturnType<typeof runLogToCallEvents>
  ) => void;
}

export function RunActivePanel({
  script,
  variables,
  sessionId,
  onCallStateCaptured,
}: RunActivePanelProps) {
  const [run, setRun] = useState<RunState>(initialRunState);
  const [ivrText, setIvrText] = useState("");
  const path = pathFromScript(script);
  const callEvents = runLogToCallEvents(run.log, path);
  const call = callFromSession(sessionId, "local-client", path.id, callEvents);
  const liveStatus = projectLiveStatus(call, path);
  const [autoListen, setAutoListen] = useState(script.setup.speechPreferences.autoListen);
  const [listenError, setListenError] = useState<string | null>(null);
  const debounceRef = useRef<number | undefined>(undefined);

  const applyPhraseNow = useCallback(
    (text: string) => {
      setRun((prev) => {
        const result = processPhrase(text, script, variables, prev);
        if (result.shouldComplete) {
          const { collected } = result.state;
          const events = runLogToCallEvents(result.state.log, path);
          const finalEvents = [
            ...events,
            newCallEvent("CALL_ENDED", {
              outcome: "COMPLETED",
              step: path.definedSteps[path.definedSteps.length - 1],
            }),
          ];
          void hashCollected(collected).then((hash) =>
            onCallStateCaptured(collected, hash, finalEvents)
          );
        }
        return result.state;
      });
    },
    [script, variables, onCallStateCaptured, path]
  );

  const applyPhraseDebounced = useCallback(
    (text: string) => {
      window.clearTimeout(debounceRef.current);
      debounceRef.current = window.setTimeout(() => applyPhraseNow(text), 150);
    },
    [applyPhraseNow]
  );

  useEffect(() => {
    if (!autoListen || run.completed) return;

    setListenError(null);
    const stop = startContinuousRecognition(
      (phrase) => applyPhraseDebounced(phrase),
      (msg) => setListenError(msg)
    );

    if (!stop) {
      setAutoListen(false);
      setListenError("Web Speech API unavailable in this browser");
      return;
    }

    return stop;
  }, [autoListen, run.completed, applyPhraseDebounced]);

  const handleManualMatch = () => {
    if (!ivrText.trim()) return;
    applyPhraseNow(ivrText.trim());
    setIvrText("");
  };

  const dismissDtmf = () => {
    setRun((prev) => ({ ...prev, pendingDtmf: undefined, pendingTrigger: undefined }));
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
        <CardTitle>{scriptDisplayName(script)}</CardTitle>
        {isSpeechRecognitionAvailable() && !run.completed && (
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
        <Tabs defaultValue="steps">
          <TabsList>
            <TabsTrigger value="steps">Steps</TabsTrigger>
            <TabsTrigger value="audit">Audit</TabsTrigger>
            <TabsTrigger value="dtmf">DTMF</TabsTrigger>
          </TabsList>

          <TabsContent value="steps" className="space-y-4 pt-4">
            <p className="text-sm text-muted-foreground">
              {autoListen
                ? "Listening locally — IVR phrases auto-match against your script."
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
            {run.pendingDtmf ? (
              <DtmfGuide
                sequence={run.pendingDtmf}
                trigger={run.pendingTrigger}
                onComplete={dismissDtmf}
              />
            ) : (
              <p className="text-sm text-muted-foreground">No pending DTMF sequence.</p>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
