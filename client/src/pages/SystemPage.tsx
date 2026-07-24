import { Monitor } from "lucide-react";
import { RuntimeHealthSection } from "./system/RuntimeHealthSection";
import { DataManagementSection } from "./system/DataManagementSection";
import { CryptoSection } from "./system/CryptoSection";
import { PageLayout } from "@/components/ui/PageHeader";
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
      subtitle="Runtime health, local data, and device crypto — former Settings live here."
      wide
    >
      <RuntimeHealthSection status={runtime} />

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
              value={automated ? "Automated (SIP / simulator)" : "Manual"}
            />
          </CardContent>
        </Card>
        <CryptoSection />
      </div>

      <DataManagementSection />
    </PageLayout>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b py-2 last:border-b-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
