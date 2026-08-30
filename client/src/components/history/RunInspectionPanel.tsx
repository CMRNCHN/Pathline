import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Anomaly, NextStep, RunInspectionReport } from "@/audit";

function severityVariant(severity: Anomaly["severity"]): "destructive" | "secondary" | "outline" {
  if (severity === "error") return "destructive";
  if (severity === "warn") return "secondary";
  return "outline";
}

interface RunInspectionPanelProps {
  report: RunInspectionReport | null;
  loading: boolean;
  onCiteEvent: (eventIndex: number) => void;
}

export function RunInspectionPanel({ report, loading, onCiteEvent }: RunInspectionPanelProps) {
  if (loading) {
    return <p className="text-sm text-muted-foreground">Inspecting local ledger…</p>;
  }
  if (!report) {
    return <p className="text-sm text-muted-foreground">Inspection is unavailable for this Run.</p>;
  }

  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-muted-foreground">Events</dt>
          <dd className="font-mono">{report.summary.eventCount}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Prompts</dt>
          <dd className="font-mono">{report.summary.promptCount}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Actions</dt>
          <dd className="font-mono">{report.summary.actionCount}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Largest gap</dt>
          <dd className="font-mono">{Math.round(report.summary.largestGapMs / 1000)}s</dd>
        </div>
      </dl>

      <div>
        <h4 className="mb-2 text-sm font-medium">Artifacts</h4>
        <ul className="space-y-1 text-sm">
          {report.artifactAvailability.map((artifact) => (
            <li key={artifact.artifact} className="flex gap-2">
              <Badge variant={artifact.available ? "secondary" : "outline"}>
                {artifact.available ? "present" : "absent"}
              </Badge>
              <span>
                <span className="font-medium">{artifact.artifact}</span>
                <span className="text-muted-foreground"> — {artifact.detail}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h4 className="mb-2 text-sm font-medium">Anomalies</h4>
        {report.anomalies.length === 0 ? (
          <p className="text-sm text-muted-foreground">No anomalies on this ledger.</p>
        ) : (
          <ul className="space-y-2">
            {report.anomalies.map((anomaly) => {
              const eventCite = anomaly.references.find(
                (cite) => cite.kind === "event" && cite.eventIndex !== undefined
              );
              return (
                <li key={anomaly.code} className="rounded-lg border p-3">
                  <div className="mb-1 flex items-center gap-2">
                    <Badge variant={severityVariant(anomaly.severity)}>{anomaly.severity}</Badge>
                    <span className="font-mono text-xs">{anomaly.code}</span>
                  </div>
                  <p className="text-sm">{anomaly.explanation}</p>
                  {eventCite?.eventIndex !== undefined ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="mt-2"
                      onClick={() => onCiteEvent(eventCite.eventIndex!)}
                    >
                      Show event
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {report.nextSteps.length > 0 ? (
        <div>
          <h4 className="mb-2 text-sm font-medium">Next steps</h4>
          <ul className="space-y-2">
            {report.nextSteps.map((step) => (
              <NextStepRow key={step.action} step={step} onCiteEvent={onCiteEvent} />
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function NextStepRow({
  step,
  onCiteEvent,
}: {
  step: NextStep;
  onCiteEvent: (eventIndex: number) => void;
}) {
  const eventCite = step.cites.find((cite) => cite.kind === "event" && cite.eventIndex !== undefined);
  return (
    <li className="flex flex-col items-start gap-2 rounded-lg border p-3">
      <div className="min-w-0">
        <p className="text-sm font-medium">{step.action}</p>
        <p className="text-xs text-muted-foreground">{step.rationale}</p>
      </div>
      {eventCite?.eventIndex !== undefined ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => onCiteEvent(eventCite.eventIndex!)}
        >
          Show event
        </Button>
      ) : null}
    </li>
  );
}
