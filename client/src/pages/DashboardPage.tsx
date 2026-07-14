import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  GitBranch,
  Play,
  Plus,
  Radio,
} from "lucide-react";
import { StatusBoard } from "@/components/StatusBoard";
import { PageLayout } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useRuntimeStatus } from "@/hooks/useRuntimeStatus";
import { loadRunHistory, subscribeRunHistory, type RunRecord } from "@/history/runHistory";
import type { AppView } from "@/navigation";
import { mergeScripts } from "@/script/selectors";
import { scriptDisplayName } from "@/script/storage";
import { useScriptStore } from "@/store/ScriptStore";

interface DashboardPageProps {
  onNavigate: (view: AppView) => void;
}

function isToday(iso: string): boolean {
  const d = new Date(iso);
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function DashboardPage({ onNavigate }: DashboardPageProps) {
  const { bundledScripts, customScripts, setActiveId, addCustom, loading, error } =
    useScriptStore();
  const [runs, setRuns] = useState<RunRecord[]>(() => loadRunHistory());

  useEffect(() => subscribeRunHistory(() => setRuns(loadRunHistory())), []);

  const workflows = mergeScripts(bundledScripts, customScripts);
  const runtime = useRuntimeStatus(
    loading,
    error,
    bundledScripts.length,
    customScripts.length
  );

  const stats = useMemo(() => {
    const today = runs.filter((r) => isToday(r.completedAt) || isToday(r.startedAt));
    const failed = runs.filter((r) => r.outcome === "failed");
    const completedToday = today.filter((r) => r.outcome === "completed").length;
    return {
      workflows: workflows.length,
      todayRuns: today.length,
      completedToday,
      issues: failed.length,
      recent: runs.slice(0, 5),
    };
  }, [runs, workflows.length]);

  const handleCreate = () => {
    const created = addCustom();
    setActiveId(created.id);
    onNavigate({ category: "edit", scriptId: created.id });
  };

  return (
    <PageLayout
      title="Dashboard"
      subtitle="What's happening on this device — build a Path, run it, or check system health."
      action={
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" onClick={() => onNavigate({ category: "workflows" })}>
            <GitBranch className="size-4" />
            Workflows
          </Button>
          <Button type="button" onClick={handleCreate}>
            <Plus className="size-4" />
            New Path
          </Button>
        </div>
      }
    >
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Workflows" value={String(stats.workflows)} icon={GitBranch} />
        <StatCard label="Runs today" value={String(stats.todayRuns)} icon={Play} />
        <StatCard label="Completed today" value={String(stats.completedToday)} icon={Activity} />
        <StatCard
          label="Issues"
          value={String(stats.issues)}
          icon={AlertTriangle}
          warn={stats.issues > 0}
        />
      </div>

      <StatusBoard status={runtime} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Quick actions</CardTitle>
            <CardDescription>Jobs you start from here.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Button type="button" variant="secondary" className="justify-start" onClick={handleCreate}>
              <Plus className="size-4" />
              Build a Path
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="justify-start"
              onClick={() => onNavigate({ category: "workflows" })}
            >
              <GitBranch className="size-4" />
              Open workflows library
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="justify-start"
              onClick={() => onNavigate({ category: "runs" })}
            >
              <Play className="size-4" />
              Review runs
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="justify-start"
              onClick={() => onNavigate({ category: "system" })}
            >
              <Radio className="size-4" />
              Check system
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-2">
              <div>
                <CardTitle className="text-base">Recent activity</CardTitle>
                <CardDescription>Latest Path runs on this device.</CardDescription>
              </div>
              <Button type="button" variant="ghost" size="sm" onClick={() => onNavigate({ category: "runs" })}>
                All runs
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {stats.recent.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No runs yet. Open a workflow and start a Run.
              </p>
            ) : (
              <ul className="m-0 flex list-none flex-col gap-2 p-0">
                {stats.recent.map((record) => (
                  <li
                    key={record.runId}
                    className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{record.pathName}</p>
                      <p className="text-xs text-muted-foreground">{formatWhen(record.completedAt)}</p>
                    </div>
                    <Badge
                      variant={
                        record.outcome === "completed"
                          ? "default"
                          : record.outcome === "failed"
                            ? "destructive"
                            : "secondary"
                      }
                    >
                      {record.outcome}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      {workflows.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Your Paths</CardTitle>
            <CardDescription>Jump back into a workflow.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {workflows.slice(0, 8).map((path) => (
              <Button
                key={path.id}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setActiveId(path.id);
                  onNavigate({ category: "edit", scriptId: path.id });
                }}
              >
                {scriptDisplayName(path)}
              </Button>
            ))}
          </CardContent>
        </Card>
      )}
    </PageLayout>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  warn,
}: {
  label: string;
  value: string;
  icon: typeof Activity;
  warn?: boolean;
}) {
  return (
    <Card size="sm" className={warn ? "border-destructive/40" : undefined}>
      <CardContent className="flex items-center gap-3 pt-0">
        <div
          className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${
            warn ? "bg-destructive/10 text-destructive" : "bg-primary/10 text-primary"
          }`}
        >
          <Icon className="size-4" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-lg font-semibold tabular-nums leading-none">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
