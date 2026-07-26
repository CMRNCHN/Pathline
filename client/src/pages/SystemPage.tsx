import { Monitor } from "lucide-react";
import { DataManagementSection } from "./system/DataManagementSection";
import { CryptoSection } from "./system/CryptoSection";
import { PageLayout } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useRuntimeStatus } from "@/hooks/useRuntimeStatus";
import { isAutomatedTransport, isTauriApp } from "@/transport/createAppTransport";
import { detectSttCapability, isSipBridgePresent } from "@/stt";
import { useScriptStore } from "@/store/ScriptStore";
import { listVaultEntries } from "@/persistence/vaultStore";

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
  const sip = isSipBridgePresent();
  const stt = detectSttCapability();
  const sealedCount = listVaultEntries().length;

  const speechReady = stt.localWhisperAvailable || stt.webSpeechAvailable;
  const speechStatus = stt.localWhisperAvailable
    ? "Ready"
    : stt.webSpeechAvailable
      ? "Browser only"
      : "Unavailable";
  const speechDetail = stt.localWhisperAvailable
    ? "Local Whisper on this device"
    : stt.webSpeechAvailable
      ? "Browser speech (manual fallback)"
      : "No speech engine available";

  const rows = [
    {
      label: "Phone line",
      status: sip || automated ? "Ready" : desktop ? "Unavailable" : "Manual only",
      detail: sip
        ? "Native SIP bridge is present"
        : desktop
          ? "Desktop SIP bridge not detected"
          : "Browser cannot automate calls",
      ok: Boolean(sip || (!desktop && !automated)),
    },
    {
      label: "Speech recognition",
      status: speechStatus,
      detail: speechDetail,
      ok: speechReady,
    },
    {
      label: "App services",
      status: runtime.api === "online" ? "Online" : runtime.api === "checking" ? "Checking…" : "Offline",
      detail: "Local API for consent and encrypted callstate",
      ok: runtime.api === "online",
    },
    {
      label: "Sealed secrets",
      status: `${sealedCount} stored`,
      detail: "Managed under Accounts — never written into Paths",
      ok: true,
    },
  ];

  const allGood = rows.every((r) => r.ok) && runtime.api === "online";

  return (
    <PageLayout
      title="System"
      subtitle="Plain-language health for the phone stack and on-device engines."
      wide
    >
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Monitor className="size-4" />
              </div>
              <div>
                <CardTitle className="text-base">Everything you need to dial</CardTitle>
                <p className="text-xs text-muted-foreground">
                  Shell: {desktop ? "Tauri desktop" : "Browser"} · Transport:{" "}
                  {automated ? "Automated" : "Manual"}
                </p>
              </div>
            </div>
            <Badge variant={allGood ? "default" : "secondary"}>
              {allGood ? "All good" : "Check details"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-1.5">
          {rows.map((row) => (
            <div
              key={row.label}
              className="flex flex-wrap items-center gap-2 rounded-md border bg-background/60 px-2.5 py-2"
            >
              <span
                className={`inline-block size-1.5 rounded-full ${row.ok ? "bg-emerald-600" : "bg-destructive"}`}
              />
              <span className="text-sm font-medium">{row.label}</span>
              <Badge variant={row.ok ? "secondary" : "destructive"}>{row.status}</Badge>
              <span className="text-xs text-muted-foreground">{row.detail}</span>
            </div>
          ))}
          <div className="pt-2">
            <button
              type="button"
              className="text-xs text-muted-foreground underline-offset-2 hover:underline"
              onClick={() => runtime.refresh()}
            >
              Refresh status
              {runtime.lastChecked
                ? ` · checked ${runtime.lastChecked.toLocaleTimeString()}`
                : ""}
            </button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <CryptoSection />
        <DataManagementSection />
      </div>
    </PageLayout>
  );
}
