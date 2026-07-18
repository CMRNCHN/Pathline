import { Activity, Hash, Mic, RefreshCw, Server, Shield, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import type { RuntimeStatus } from "../hooks/useRuntimeStatus";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatusBoardProps {
  status: RuntimeStatus;
}

type TileState = "ok" | "warn" | "busy" | "idle" | "err";

interface Tile {
  id: string;
  icon: typeof Server;
  label: string;
  value: string;
  state: TileState;
  delay: number;
}

function relativeCheck(when: Date | null): string {
  if (!when) return "checking…";
  const sec = Math.round((Date.now() - when.getTime()) / 1000);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  return `${Math.floor(sec / 60)}m ago`;
}

function tileBadgeVariant(state: TileState) {
  switch (state) {
    case "ok":
      return "default" as const;
    case "warn":
      return "secondary" as const;
    case "busy":
      return "outline" as const;
    case "err":
      return "destructive" as const;
    case "idle":
      return "ghost" as const;
  }
}

function buildTiles(status: RuntimeStatus): Tile[] {
  const apiState: TileState =
    status.api === "checking" ? "busy" : status.api === "online" ? "ok" : "err";

  const templateState: TileState =
    status.templates === "loading"
      ? "busy"
      : status.templates === "error"
        ? "err"
        : status.templateCount > 0
          ? "ok"
          : "warn";

  return [
    {
      id: "api",
      icon: Server,
      label: "API",
      value:
        status.api === "checking"
          ? "Checking…"
          : status.api === "online"
            ? "Online"
            : "Offline",
      state: apiState,
      delay: 0,
    },
    {
      id: "templates",
      icon: Sparkles,
      label: "Workflows",
      value:
        status.templates === "loading"
          ? "Loading…"
          : status.templates === "error"
            ? "Error"
            : `${status.templateCount} loaded`,
      state: templateState,
      delay: 60,
    },
    {
      id: "dtmf",
      icon: Hash,
      label: "Keypad",
      value: "Active",
      state: "ok",
      delay: 120,
    },
    {
      id: "voice",
      icon: Mic,
      label: "Voice",
      value: "Planned",
      state: "idle",
      delay: 150,
    },
    {
      id: "vault",
      icon: Shield,
      label: "Vault",
      value: status.vault === "ready" ? "Key active" : "Idle until run",
      state: status.vault === "ready" ? "ok" : "idle",
      delay: 180,
    },
    {
      id: "mode",
      icon: Activity,
      label: "Mode",
      value: status.apiMode?.replace(/_/g, " ") ?? "Client-mediated",
      state: "ok",
      delay: 240,
    },
  ];
}

export function StatusBoard({ status }: StatusBoardProps) {
  const tiles = buildTiles(status);
  const onlineCount = tiles.filter((t) => t.state === "ok").length;
  const hasIssue = tiles.some((t) => t.state === "err");
  const [, tick] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => tick((n) => n + 1), 5000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <Card
      className={cn(
        "surface-contrast relative mb-5 overflow-hidden py-3 shadow-md ring-1 ring-black/10",
        hasIssue && "border-destructive/35"
      )}
      aria-label="Runtime status"
    >
      <div
        className="pointer-events-none absolute inset-0 bg-linear-to-r from-transparent via-primary/5 to-transparent opacity-60"
        aria-hidden
      />

      <CardContent className="relative z-1 space-y-3 px-3.5 pb-1 pt-0">
        <div className="flex items-center gap-2.5">
          <span className="text-[0.65rem] font-bold uppercase tracking-widest text-muted-foreground">
            Runtime
          </span>
          <span className="flex-1 font-mono text-[0.72rem] text-muted-foreground/80">
            {onlineCount}/{tiles.length} healthy · {relativeCheck(status.lastChecked)}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={() => void status.refresh()}
            title="Refresh status"
          >
            <RefreshCw className="size-3" />
            Refresh
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {tiles.map((tile) => {
            const Icon = tile.icon;
            return (
              <Card
                key={tile.id}
                size="sm"
                className="animate-[status-tile-in_0.45s_ease_both] border-0 bg-black/15 py-2 shadow-none dark:bg-black/8"
                style={{ animationDelay: `${tile.delay}ms` }}
              >
                <CardContent className="flex items-center gap-2 px-2 py-0">
                  <Badge
                    variant={tileBadgeVariant(tile.state)}
                    className={cn(
                      "absolute top-1.5 right-1.5 size-1.5 rounded-full border-0 p-0",
                      tile.state === "ok" && "animate-pulse bg-emerald-500",
                      tile.state === "warn" && "animate-pulse bg-amber-500",
                      tile.state === "busy" && "animate-pulse bg-primary",
                      tile.state === "err" && "animate-pulse bg-destructive",
                      tile.state === "idle" && "bg-muted-foreground/40"
                    )}
                    aria-hidden
                  />
                  <span className="text-muted-foreground">
                    <Icon size={14} strokeWidth={2} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[0.65rem] font-medium text-muted-foreground">
                      {tile.label}
                    </p>
                    <p className="truncate text-xs font-medium">{tile.value}</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="h-0.5 overflow-hidden rounded-full bg-muted" aria-hidden>
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{ width: `${(onlineCount / tiles.length) * 100}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
