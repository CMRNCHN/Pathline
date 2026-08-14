import { Download, HardDrive } from "lucide-react";
import { clearLocalKeys } from "@/crypto";
import { clearRunHistory, loadRunHistory } from "@/history/runHistory";
import { clearAllPersistence } from "@/persistence";
import { clearVaultEntries } from "@/persistence/vaultStore";
import { mergeScripts } from "@/script/selectors";
import { useScriptStore } from "@/store/ScriptStore";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DataManagementSection() {
  const { customScripts, bundledScripts } = useScriptStore();
  const paths = mergeScripts(bundledScripts, customScripts);
  const runCount = loadRunHistory().length;

  const exportAll = () => {
    const blob = new Blob([JSON.stringify(paths, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "pathline-paths.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearAllLocalData = async () => {
    if (!confirm("Delete all Paths, Run History, Accounts, Vault entries, and local data?")) return;
    await Promise.all([clearAllPersistence(), clearRunHistory()]);
    clearVaultEntries();
    clearLocalKeys();
    localStorage.removeItem("pathline-accounts");
    localStorage.clear();
    sessionStorage.clear();
    if ("caches" in window) {
      const names = await caches.keys();
      await Promise.all(names.map((name) => caches.delete(name)));
    }
    window.location.reload();
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <HardDrive className="size-4" />
          </div>
          <CardTitle>Local data</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p className="text-muted-foreground">
          {customScripts.length} custom Path{customScripts.length === 1 ? "" : "s"} ·{" "}
          {bundledScripts.length} bundled · {runCount} run{runCount === 1 ? "" : "s"} in history
        </p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled={paths.length === 0} onClick={exportAll}>
            <Download className="size-4" />
            Export Paths
          </Button>
          <Button type="button" variant="destructive" onClick={() => void clearAllLocalData()}>
            Clear all local data
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
