import type { ElementType, ReactNode } from "react";
import { Shield, Activity, HardDrive, Download, Info } from "lucide-react";
import { PageLayout } from "../components/ui/PageHeader";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { useScriptStore } from "../store/ScriptStore";
import { mergeScripts } from "../script/selectors";
import { clearLocalKeys } from "../crypto";
import { ACTIVE_SCRIPT_KEY, CUSTOM_SCRIPTS_KEY } from "../script/storage";
import { clearRunHistory, loadRunHistory } from "../history/runHistory";

function StatusRow({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b py-2.5 last:border-b-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      {ok !== undefined ? (
        <Badge variant={ok ? "default" : "secondary"}>{value}</Badge>
      ) : (
        <span className="text-sm font-medium">{value}</span>
      )}
    </div>
  );
}

function SettingsCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: ElementType;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Icon className="size-4" aria-hidden />
          </div>
          <CardTitle>{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function SettingsPage() {
  const { customScripts, bundledScripts, loading, error } = useScriptStore();
  const paths = mergeScripts(bundledScripts, customScripts);
  const runCount = loadRunHistory().length;

  const exportAll = () => {
    const blob = new Blob([JSON.stringify(paths, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "pathline-workflows.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearAllLocalData = () => {
    if (!confirm("Delete all Workflows, Run History, and local data? This cannot be undone.")) return;
    localStorage.removeItem(CUSTOM_SCRIPTS_KEY);
    localStorage.removeItem(ACTIVE_SCRIPT_KEY);
    clearRunHistory();
    clearLocalKeys();
    window.location.reload();
  };

  return (
    <PageLayout
      title="Settings"
      subtitle="Privacy, health, and local data — everything Pathline keeps on your device."
      wide
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SettingsCard title="Privacy" icon={Shield}>
          <StatusRow label="Secrets & target numbers" value="Device only" ok />
          <StatusRow label="Call audio" value="Processed locally" ok />
          <StatusRow label="Status reporting" value="Encrypted blob + hash" ok />
          <StatusRow label="Retention" value="Auto-purged; revoke anytime" ok />
          <p className="mt-4 border-t pt-4 text-sm text-muted-foreground">
            Carriers still see call metadata on the PSTN.
          </p>
        </SettingsCard>

        <SettingsCard title="Health" icon={Activity}>
          <StatusRow label="Phone keypad" value="Active — required for a Run" ok />
          <StatusRow label="Voice input" value="Planned — not used yet" />
          <StatusRow label="API endpoint" value="/api → :8000" ok />
          <StatusRow label="Workflows loaded" value={`${paths.length}`} ok={paths.length > 0} />
          <StatusRow
            label="API sync"
            value={loading ? "Loading…" : error ? "Error" : "Ready"}
            ok={!error && !loading}
          />
        </SettingsCard>

        <SettingsCard title="Local data" icon={HardDrive}>
          <StatusRow label="Your Workflows" value={`${customScripts.length} saved`} />
          <StatusRow label="Example Workflows" value={`${bundledScripts.length} bundled`} />
          <StatusRow label="Run History" value={`${runCount} recorded`} />
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              type="button"
              variant="link"
              className="h-auto px-0"
              onClick={() => {
                clearLocalKeys();
                alert("Session encryption keys cleared.");
              }}
            >
              Clear encryption keys
            </Button>
            <Button
              type="button"
              variant="link"
              className="h-auto px-0 text-destructive hover:text-destructive"
              onClick={clearAllLocalData}
            >
              Clear all local data
            </Button>
          </div>
        </SettingsCard>

        <SettingsCard title="Export all Workflows" icon={Download}>
          <p className="mb-4 text-sm text-muted-foreground">
            Download {paths.length} Workflow{paths.length !== 1 ? "s" : ""} as JSON. Workflows never
            contain Input values.
          </p>
          <Button type="button" disabled={paths.length === 0} onClick={exportAll}>
            Download Workflows
          </Button>
        </SettingsCard>

        <SettingsCard title="About" icon={Info}>
          <p className="text-sm text-muted-foreground">
            Pathline · Client-mediated · DTMF Runs · Encrypted Status export
          </p>
        </SettingsCard>
      </div>
    </PageLayout>
  );
}
