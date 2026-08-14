import { useMemo } from "react";
import { PathList } from "./paths/PathList";
import { PathDetail } from "./paths/PathDetail";
import { useScriptStore } from "@/store/ScriptStore";
import { mergeScripts } from "@/script/selectors";
import type { AppView } from "@/navigation";
import { PageLayout } from "@/components/ui/PageHeader";

interface PathsPageProps {
  pathId?: string;
  panel?: "edit" | "run";
  onNavigate: (view: AppView) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export function PathsPage({
  pathId,
  panel = "edit",
  onNavigate,
  searchQuery,
  onSearchChange,
}: PathsPageProps) {
  const { bundledScripts, customScripts, setActiveId, addCustom } = useScriptStore();
  const query = searchQuery;
  const setQuery = onSearchChange;

  const paths = mergeScripts(bundledScripts, customScripts);

  const filtered = useMemo(() => {
    if (!query.trim()) return paths;
    const q = query.toLowerCase();
    return paths.filter(
      (p) =>
        p.setup.name.toLowerCase().includes(q) ||
        p.setup.description.toLowerCase().includes(q)
    );
  }, [paths, query]);

  const handleCreate = () => {
    const created = addCustom();
    setActiveId(created.id);
    onNavigate({ category: "paths", pathId: created.id, panel: "edit" });
  };

  return (
    <PageLayout
      title="Path Library"
      subtitle="Scripted calls on this device — edit Steps or dial from the same Path."
      wide
    >
      <div className="grid min-h-[28rem] grid-cols-1 gap-4 lg:grid-cols-[minmax(16rem,22rem)_1fr]">
        <PathList
          paths={filtered}
          selectedId={pathId}
          searchQuery={query}
          onSearchChange={setQuery}
          onSelect={(id) => onNavigate({ category: "paths", pathId: id, panel: "edit" })}
          onCreate={handleCreate}
        />
        <div className="min-h-[24rem] rounded-xl border bg-card/30 p-3 md:p-4">
          {pathId ? (
            <PathDetail pathId={pathId} panel={panel} onNavigate={onNavigate} />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Select a Path or create a new one.
            </div>
          )}
        </div>
      </div>
    </PageLayout>
  );
}
