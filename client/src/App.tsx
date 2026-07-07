import { useEffect, useState } from "react";
import { Shell } from "./components/Shell";
import { LibraryPage } from "./pages/LibraryPage";
import { EditPage } from "./pages/EditPage";
import { RunPage } from "./pages/RunPage";
import { ScriptSettingsPage } from "./pages/ScriptSettingsPage";
import { SystemPage } from "./pages/SystemPage";
import { SettingsPage } from "./pages/SettingsPage";
import { useScriptStore } from "./store/ScriptStore";
import { getActiveScript } from "./script/selectors";
import type { AppView } from "./navigation";

export default function App() {
  const { setActiveId, bundledScripts, customScripts } = useScriptStore();
  const [view, setView] = useState<AppView>({ category: "library" });
  const [searchQuery, setSearchQuery] = useState("");

  const navigate = (next: AppView) => {
    setView(next);
    if (next.category === "edit" || next.category === "run" || next.category === "script-settings") {
      setActiveId(next.scriptId);
    }
  };

  useEffect(() => {
    if (view.category === "edit" || view.category === "run" || view.category === "script-settings") {
      const exists = getActiveScript(bundledScripts, customScripts, view.scriptId);
      if (!exists) setView({ category: "library" });
    }
  }, [view, bundledScripts, customScripts]);

  return (
    <Shell
      view={view}
      onNavigate={navigate}
      searchQuery={searchQuery}
      onSearchChange={setSearchQuery}
    >
      {view.category === "library" && (
        <LibraryPage onNavigate={navigate} searchQuery={searchQuery} />
      )}

      {view.category === "edit" && (
        <EditPage scriptId={view.scriptId} onNavigate={navigate} />
      )}

      {view.category === "run" && <RunPage scriptId={view.scriptId} />}

      {view.category === "script-settings" && (
        <ScriptSettingsPage scriptId={view.scriptId} onNavigate={navigate} />
      )}

      {view.category === "system" && <SystemPage />}

      {view.category === "settings" && <SettingsPage />}
    </Shell>
  );
}
