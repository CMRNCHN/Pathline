import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { CallStateBoard } from "@/components/CallStateBoard";
import { LedgerEventRow } from "@/components/history/LedgerEventRow";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { diffStatus, statusAtOffset } from "@/audit/cursor";
import type { CallEvent } from "@/callstate";

interface RunReplayPanelProps {
  runId: string;
  pathId: string;
  pathIntent: string;
  definedSteps: string[];
  events: CallEvent[];
  selectedIndex: number;
  onSelectedIndexChange: (index: number) => void;
}

export function RunReplayPanel({
  runId,
  pathId,
  pathIntent,
  definedSteps,
  events,
  selectedIndex,
  onSelectedIndexChange,
}: RunReplayPanelProps) {
  const [compareFrom, setCompareFrom] = useState<number | null>(null);
  const maxIndex = Math.max(events.length - 1, 0);
  const offset = events.length === 0 ? 0 : Math.min(Math.max(selectedIndex, 0), maxIndex);

  const liveStatus = useMemo(
    () => statusAtOffset(runId, pathId, definedSteps, events, offset),
    [definedSteps, events, offset, pathId, runId]
  );

  useEffect(() => {
    document.getElementById(`ledger-event-${offset}`)?.scrollIntoView({ block: "nearest" });
  }, [offset]);

  const diff = useMemo(() => {
    if (compareFrom === null || events.length === 0) return null;
    const from = statusAtOffset(runId, pathId, definedSteps, events, compareFrom);
    return diffStatus(from, liveStatus);
  }, [compareFrom, definedSteps, events, liveStatus, pathId, runId]);

  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No ledger events were stored for this Run.</p>;
  }

  return (
    <div className="@container">
      <div className="grid gap-4 @3xl:grid-cols-[minmax(0,1fr)_minmax(16rem,18rem)]">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              aria-label="Previous event"
              disabled={offset <= 0}
              onClick={() => onSelectedIndexChange(offset - 1)}
            >
              <ChevronLeft />
            </Button>
            <input
              type="range"
              min={0}
              max={maxIndex}
              value={offset}
              aria-label="Replay timeline"
              className="h-2 w-full accent-foreground"
              onChange={(event) => onSelectedIndexChange(Number(event.target.value))}
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              aria-label="Next event"
              disabled={offset >= maxIndex}
              onClick={() => onSelectedIndexChange(offset + 1)}
            >
              <ChevronRight />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Event {offset + 1} of {events.length}
            {compareFrom !== null ? ` · compared with ${compareFrom}` : ""}
          </p>
          <ScrollArea className="h-64 rounded-lg border">
            <ul className="p-1">
              {events.map((event, index) => (
                <li key={event.id}>
                  <LedgerEventRow
                    event={event}
                    index={index}
                    active={index === offset}
                    onSelect={onSelectedIndexChange}
                  />
                </li>
              ))}
            </ul>
          </ScrollArea>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setCompareFrom((current) => (current === offset ? null : offset))}
          >
            {compareFrom === offset ? "Clear compare anchor" : "Diff from this event"}
          </Button>
          {diff ? (
            <p className="text-xs text-muted-foreground">
              {diff.phaseChanged ? `Phase changed. ` : ""}
              {diff.activeStepChanged ? `Active step changed. ` : ""}
              {diff.addedSteps.length ? `Added: ${diff.addedSteps.join(", ")}. ` : ""}
              {diff.removedSteps.length ? `Removed: ${diff.removedSteps.join(", ")}.` : ""}
              {!diff.phaseChanged &&
              !diff.activeStepChanged &&
              diff.addedSteps.length === 0 &&
              diff.removedSteps.length === 0
                ? "No step or phase change between anchors."
                : ""}
            </p>
          ) : null}
        </div>
        <CallStateBoard
          liveStatus={liveStatus}
          path={{ id: pathId, intent: pathIntent, definedSteps }}
          label="State at cursor"
        />
      </div>
    </div>
  );
}
