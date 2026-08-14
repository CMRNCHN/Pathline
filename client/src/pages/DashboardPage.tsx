import { useEffect, useMemo, useState } from "react";
import { GitBranch, KeyRound, Plus, Users } from "lucide-react";
import { PageLayout } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { loadRunHistory, subscribeRunHistory, type RunRecord } from "@/history/runHistory";
import type { AppView } from "@/navigation";
import { createAccount, listAccounts } from "@/persistence/accountsStore";
import { listVaultEntries } from "@/persistence/vaultStore";
import { mergeScripts } from "@/script/selectors";
import { scriptDisplayName } from "@/script/storage";
import { useScriptStore } from "@/store/ScriptStore";

interface DashboardPageProps {
  onNavigate: (view: AppView) => void;
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function outcomeVariant(outcome: RunRecord["outcome"]) {
  if (outcome === "completed") return "default" as const;
  if (outcome === "failed") return "destructive" as const;
  return "secondary" as const;
}

export function DashboardPage({ onNavigate }: DashboardPageProps) {
  const { bundledScripts, customScripts, setActiveId, addCustom } = useScriptStore();
  const [runs, setRuns] = useState<RunRecord[]>(() => loadRunHistory());
  const [accountCount, setAccountCount] = useState(() => listAccounts().length);
  const [secretCount, setSecretCount] = useState(() => listVaultEntries().length);

  useEffect(() => subscribeRunHistory(() => setRuns(loadRunHistory())), []);

  useEffect(() => {
    setAccountCount(listAccounts().length);
    setSecretCount(listVaultEntries().length);
  }, []);

  const paths = useMemo(
    () => mergeScripts(bundledScripts, customScripts),
    [bundledScripts, customScripts]
  );

  const latestByPath = useMemo(() => {
    const map = new Map<string, RunRecord>();
    for (const run of runs) {
      if (!map.has(run.pathId)) map.set(run.pathId, run);
    }
    return map;
  }, [runs]);

  const pathRows = useMemo(() => {
    return paths.map((path) => {
      const latest = latestByPath.get(path.id);
      return {
        id: path.id,
        name: scriptDisplayName(path),
        latest,
      };
    });
  }, [paths, latestByPath]);

  const succeeded = runs.filter((r) => r.outcome === "completed").length;
  const failed = runs.filter((r) => r.outcome === "failed").length;

  const handleNewPath = () => {
    const created = addCustom();
    setActiveId(created.id);
    onNavigate({ category: "paths", pathId: created.id, panel: "edit" });
  };

  const handleNewAccount = () => {
    const created = createAccount();
    setAccountCount(listAccounts().length);
    onNavigate({ category: "accounts", accountId: created.id });
  };

  const actions = [
    {
      label: "New Path",
      hint: "Build a call flow",
      icon: Plus,
      onClick: handleNewPath,
      primary: true,
    },
    {
      label: "Dial Path",
      hint: "Open Path Library",
      icon: GitBranch,
      onClick: () => onNavigate({ category: "paths" }),
      primary: false,
    },
    {
      label: "Add Profile",
      hint: "Local inputs only",
      icon: Users,
      onClick: handleNewAccount,
      primary: false,
    },
    {
      label: "Sealed secrets",
      hint: `${secretCount} on device`,
      icon: KeyRound,
      onClick: () => onNavigate({ category: "accounts", panel: "secrets" }),
      primary: false,
    },
  ];

  return (
    <PageLayout title="Dashboard" subtitle="Latest Path status and shortcuts.">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        {[
          { label: "Paths", value: String(paths.length), sub: "in library" },
          { label: "Succeeded", value: String(succeeded), sub: "runs ok" },
          { label: "Failed", value: String(failed), sub: "needs attention" },
          { label: "Accounts", value: String(accountCount), sub: "profiles" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-md border bg-card px-2.5 py-2 shadow-sm">
            <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
              {stat.label}
            </div>
            <div className="mt-0.5 text-lg font-semibold tabular-nums leading-tight">{stat.value}</div>
            <div className="text-[11px] text-muted-foreground">{stat.sub}</div>
          </div>
        ))}
      </div>

      <div>
        <div className="mb-1.5 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          Quick actions
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.label}
                type="button"
                onClick={action.onClick}
                className={`rounded-md border px-2.5 py-2 text-left shadow-sm transition-colors ${
                  action.primary
                    ? "border-primary bg-primary text-primary-foreground hover:opacity-90"
                    : "border-border bg-card hover:bg-accent"
                }`}
              >
                <Icon
                  className={`mb-1.5 size-3.5 ${
                    action.primary ? "text-primary-foreground/80" : "text-muted-foreground"
                  }`}
                />
                <div className="text-xs font-semibold leading-tight">{action.label}</div>
                <div
                  className={`mt-0.5 text-[10px] ${
                    action.primary ? "text-primary-foreground/70" : "text-muted-foreground"
                  }`}
                >
                  {action.hint}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
            Path status
          </div>
          <span className="text-[10px] font-mono text-muted-foreground">Latest run per Path</span>
        </div>
        <div className="overflow-hidden rounded-md border bg-card shadow-sm">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b bg-muted/50">
                {["Path", "Result", "When", ""].map((h) => (
                  <th
                    key={h || "act"}
                    className="px-2.5 py-1.5 text-left font-mono text-[10px] font-medium uppercase tracking-wider text-muted-foreground"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pathRows.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-2.5 py-4 text-muted-foreground">
                    No Paths yet. Create one from Quick actions.
                  </td>
                </tr>
              ) : (
                pathRows.map((row) => (
                  <tr key={row.id} className="border-b last:border-0 hover:bg-accent/40">
                    <td className="px-2.5 py-1.5 font-medium">{row.name}</td>
                    <td className="px-2.5 py-1.5">
                      {row.latest ? (
                        <Badge variant={outcomeVariant(row.latest.outcome)}>{row.latest.outcome}</Badge>
                      ) : (
                        <Badge variant="secondary">Never run</Badge>
                      )}
                    </td>
                    <td className="px-2.5 py-1.5 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                      {row.latest ? formatWhen(row.latest.completedAt) : "—"}
                    </td>
                    <td className="px-2.5 py-1.5 text-right">
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          onNavigate({
                            category: "paths",
                            pathId: row.id,
                            panel: row.latest ? "run" : "edit",
                          })
                        }
                      >
                        Open
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </PageLayout>
  );
}
