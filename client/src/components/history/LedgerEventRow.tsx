import { eventInputMetadata, LEDGER_LEGACY_CHAIN_HASH_KEY, type CallEvent } from "@/callstate";
import { cn } from "@/lib/utils";

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleTimeString("en-GB", { hour12: false });
}

function metaSummary(event: CallEvent): string {
  const input = eventInputMetadata(event.metadata);
  const parts: string[] = [];
  if (typeof input.step === "string") parts.push(input.step);
  if (typeof input.phraseLength === "number") parts.push(`${input.phraseLength} chars`);
  if (typeof input.digits === "number") parts.push(`${input.digits} keys`);
  if (typeof input.transport === "string") parts.push(input.transport);
  if (typeof input.outcome === "string") parts.push(input.outcome);
  const digest = input[LEDGER_LEGACY_CHAIN_HASH_KEY];
  if (typeof digest === "string" && digest.length >= 8) parts.push(`hash ${digest.slice(0, 8)}…`);
  return parts.join(" · ");
}

interface LedgerEventRowProps {
  event: CallEvent;
  index: number;
  active?: boolean;
  onSelect?: (index: number) => void;
}

export function LedgerEventRow({ event, index, active, onSelect }: LedgerEventRowProps) {
  const summary = metaSummary(event);
  return (
    <button
      type="button"
      onClick={() => onSelect?.(index)}
      className={cn(
        "flex w-full items-start gap-3 rounded-md px-2.5 py-2 text-left text-sm transition-colors",
        active ? "bg-muted" : "hover:bg-muted/50"
      )}
    >
      <span className="w-8 shrink-0 font-mono text-xs text-muted-foreground">{index}</span>
      <span className="w-[4.5rem] shrink-0 font-mono text-xs text-muted-foreground">
        {formatTime(event.timestamp)}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block font-medium">{event.type}</span>
        {summary ? <span className="block text-xs text-muted-foreground">{summary}</span> : null}
      </span>
    </button>
  );
}
