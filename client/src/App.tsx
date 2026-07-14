import { useEffect, useState } from "react";
import { Shell } from "./components/Shell";
import { DashboardPage } from "./pages/DashboardPage";
import { PathsPage } from "./pages/PathsPage";
import { EditPage } from "./pages/EditPage";
import { RunPage } from "./pages/RunPage";
import { RunsPage } from "./pages/HistoryPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { SystemPage } from "./pages/SystemPage";
import { VaultPage } from "./pages/VaultPage";
import { SettingsPage } from "./pages/SettingsPage";
import { useScriptStore } from "./store/ScriptStore";
import { getActiveScript } from "./script/selectors";
import type { AppView } from "./navigation";

export default function App() {
  const { setActiveId, bundledScripts, customScripts } = useScriptStore();
  const [view, setView] = useState<AppView>({ category: "dashboard" });
  const [searchQuery, setSearchQuery] = useState("");

  const navigate = (next: AppView) => {
    setView(next);
    if (next.category === "edit" || next.category === "run") {
      setActiveId(next.scriptId);
    }
  };

  useEffect(() => {
    if (view.category === "edit" || view.category === "run") {
      const exists = getActiveScript(bundledScripts, customScripts, view.scriptId);
      if (!exists) setView({ category: "workflows" });
    }
  }, [view, bundledScripts, customScripts]);

  return (
    <Shell
      view={view}
      onNavigate={navigate}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
    >
      {view.category === "dashboard" && <DashboardPage onNavigate={navigate} />}

      {view.category === "workflows" && (
        <PathsPage onNavigate={navigate} searchQuery={searchQuery} />
      )}

      {view.category === "runs" && <RunsPage />}

      {view.category === "templates" && <TemplatesPage onNavigate={navigate} />}

      {view.category === "system" && <SystemPage />}

      {view.category === "vault" && <VaultPage />}

      {view.category === "edit" && (
        <EditPage scriptId={view.scriptId} onNavigate={navigate} />
      )}

      {view.category === "run" && <RunPage scriptId={view.scriptId} />}

      {view.category === "settings" && <SettingsPage />}
    </Shell>
  );
}
