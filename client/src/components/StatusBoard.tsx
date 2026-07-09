import { Activity, Hash, Server, Shield, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import type { RuntimeStatus } from "../hooks/useRuntimeStatus";

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
      label: "Scripts",
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
      id: "input",
      icon: Hash,
      label: "Input",
      value: "DTMF keypad",
      state: "ok",
      delay: 120,
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
    <section
      className={`status-board${hasIssue ? " status-board-alert" : ""}`}
      aria-label="Runtime status"
    >
      <div className="status-board-scan" aria-hidden />
      <div className="status-board-head">
        <span className="status-board-title">Runtime</span>
        <span className="status-board-meta">
          {onlineCount}/{tiles.length} healthy · {relativeCheck(status.lastChecked)}
        </span>
        <button
          type="button"
          className="status-board-refresh"
          onClick={() => void status.refresh()}
          title="Refresh status"
        >
          Refresh
        </button>
      </div>

      <div className="status-board-track">
        {tiles.map((tile) => {
          const Icon = tile.icon;
          return (
            <div
              key={tile.id}
              className={`status-tile status-tile-${tile.state}`}
              style={{ animationDelay: `${tile.delay}ms` }}
            >
              <span className="status-tile-beacon" aria-hidden />
              <span className="status-tile-icon">
                <Icon size={14} strokeWidth={2} />
              </span>
              <span className="status-tile-body">
                <span className="status-tile-label">{tile.label}</span>
                <span className="status-tile-value">{tile.value}</span>
              </span>
            </div>
          );
        })}
      </div>

      <div className="status-board-rail" aria-hidden>
        <span
          className="status-board-rail-fill"
          style={{ width: `${(onlineCount / tiles.length) * 100}%` }}
        />
      </div>
    </section>
  );
}
