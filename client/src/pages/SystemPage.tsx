import { Monitor, Radio, Shield } from "lucide-react";
import { StatusBoard } from "@/components/StatusBoard";
import { PageLayout } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRuntimeStatus } from "@/hooks/useRuntimeStatus";
import { isAutomatedTransport, isTauriApp } from "@/transport/createAppTransport";
import { useScriptStore } from "@/store/ScriptStore";

export function SystemPage() {
  const { bundledScripts, customScripts, loading, error } = useScriptStore();
  const runtime = useRuntimeStatus(
    loading,
    error,
    bundledScripts.length,
    customScripts.length
  );

  const desktop = isTauriApp();
  const automated = isAutomatedTransport();

  return (
    <PageLayout
      title="System"
      subtitle="Operate PromptPath — health of the local client, API sidecar, and call stack."
    >
      <StatusBoard status={runtime} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Monitor className="size-4" />
              </div>
              <CardTitle>Runtime</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="Shell" value={desktop ? "Tauri desktop" : "Browser"} />
            <Row
              label="Call transport"
              value={automated ? "Automated (SIP / simulator)" : "Manual browser"}
            />
            <Row label="API proxy" value="/api → :8000" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Shield className="size-4" />
              </div>
              <CardTitle>Privacy boundary</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p className="text-muted-foreground">
              Secrets, targets, and audio stay on this device. The API only receives consent
              tokens and encrypted callstate blobs.
            </p>
            <Badge variant="secondary">Client-mediated</Badge>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Radio className="size-4" />
              </div>
              <CardTitle>How to troubleshoot</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-1 text-sm text-muted-foreground">
            <p>1. Confirm API shows Online on the Runtime board.</p>
            <p>2. For live calls, use the desktop app (SIP bridge lands in a later wave).</p>
            <p>3. Failed Runs appear under Runs — open one to inspect captured fields.</p>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b py-2 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
