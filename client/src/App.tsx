import { useEffect, useState } from "react";
import { Shell } from "./components/Shell";
import { DashboardPage } from "./pages/DashboardPage";
import { PathsPage } from "./pages/PathsPage";
import { AccountsPage } from "./pages/AccountsPage";
import { SystemPage } from "./pages/SystemPage";
import { VaultPage } from "./pages/VaultPage";
import { useScriptStore } from "./store/ScriptStore";
import { getActiveScript } from "./script/selectors";
import type { AppView } from "./navigation";

export default function App() {
  const { setActiveId, bundledScripts, customScripts } = useScriptStore();
  const [view, setView] = useState<AppView>({ category: "dashboard" });
  const [searchQuery, setSearchQuery] = useState("");

  const navigate = (next: AppView) => {
    setView(next);
    if (next.category === "paths" && next.pathId) {
      setActiveId(next.pathId);
    }
  };

  useEffect(() => {
    if (view.category === "paths" && view.pathId) {
      const exists = getActiveScript(bundledScripts, customScripts, view.pathId);
      if (!exists) setView({ category: "paths" });
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

      {view.category === "paths" && (
        <PathsPage
          pathId={view.pathId}
          panel={view.panel}
          onNavigate={navigate}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
        />
      )}

      {view.category === "accounts" && (
        <AccountsPage accountId={view.accountId} onNavigate={navigate} />
      )}

      {view.category === "vault" && <VaultPage />}

      {view.category === "system" && <SystemPage />}
    </Shell>
  );
}
