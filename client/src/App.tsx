import { useEffect, useState } from "react";
import { Play } from "lucide-react";
import { AppSidebar, type AppView } from "./components/AppSidebar";
import { ScriptLibrary } from "./components/ScriptLibrary";
import { ScriptEditor } from "./components/ScriptEditor";
import { RunPanel } from "./components/RunPanel";
import { SystemPanel } from "./components/SystemPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { PageShell } from "./components/ui/PageShell";
import { useScriptStore } from "./store/ScriptStore";
import { getActiveScript } from "./script/selectors";

export default function App() {
  const { setActiveId, bundledScripts, customScripts } = useScriptStore();
  const [view, setView] = useState<AppView>({ category: "library" });
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (view.category === "edit" || view.category === "run") {
      setActiveId(view.scriptId);
    }
  }, [view, setActiveId]);

  const runScript =
    view.category === "run"
      ? getActiveScript(bundledScripts, customScripts, view.scriptId)
      : undefined;

  return (
    <div className="flex h-screen w-full bg-canvas font-sans text-ink overflow-hidden">
      <AppSidebar
        view={view}
        onNavigate={setView}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <main className="flex-1 overflow-y-auto bg-canvas">
        {view.category === "library" && (
          <ScriptLibrary onNavigate={setView} searchQuery={searchQuery} />
        )}

        {view.category === "edit" && (
          <ScriptEditor
            scriptId={view.scriptId}
            onTest={(id) => setView({ category: "run", scriptId: id })}
          />
        )}

        {view.category === "run" && (
          <div className="min-h-full">
            <PageShell
              title={runScript?.name || "Run Template"}
              subtitle="Execute this script locally. Secrets and audio stay on your device."
              action={
                <div className="flex items-center gap-2 text-xs text-muted bg-white border border-[#0a0a0b14] px-3 py-1.5 rounded-md">
                  <Play className="w-3.5 h-3.5 text-accent" />
                  Client-mediated run
                </div>
              }
            >
              <RunPanel />
            </PageShell>
          </div>
        )}

        {view.category === "system" && <SystemPanel id={view.id} />}

        {view.category === "settings" && <SettingsPanel />}
      </main>
    </div>
  );
}
