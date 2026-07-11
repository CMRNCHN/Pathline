import { useMemo } from "react";
import { GitBranch, Phone, Plus } from "lucide-react";
import { StatusBoard } from "../components/StatusBoard";
import { useRuntimeStatus } from "../hooks/useRuntimeStatus";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript, mergeScripts } from "../script/selectors";
import { PageLayout } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { Badge } from "../components/ui/Badge";
import { scriptDisplayName } from "../script/storage";
import { isPlaceholderRule } from "../script/ruleIntent";
import { getPathReadiness, READINESS_LABEL } from "../script/pathReadiness";
import type { AppView } from "../navigation";

interface PathsPageProps {
  onNavigate: (view: AppView) => void;
  searchQuery: string;
}

export function PathsPage({ onNavigate, searchQuery }: PathsPageProps) {
  const { bundledScripts, customScripts, setActiveId, addCustom, loading, error } =
    useScriptStore();

  const runtime = useRuntimeStatus(
    loading,
    error,
    bundledScripts.length,
    customScripts.length
  );

  const paths = mergeScripts(bundledScripts, customScripts);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return paths;
    const q = searchQuery.toLowerCase();
    return paths.filter(
      (p) =>
        p.setup.name.toLowerCase().includes(q) ||
        p.setup.description.toLowerCase().includes(q)
    );
  }, [paths, searchQuery]);

  const openPath = (id: string) => {
    setActiveId(id);
    onNavigate({ category: "edit", scriptId: id });
  };

  const handleCreate = () => {
    const created = addCustom();
    setActiveId(created.id);
    onNavigate({ category: "edit", scriptId: created.id });
  };

  return (
    <PageLayout
      title="Paths"
      subtitle="A Path is a call workflow. Open one to edit its Steps, or Run it on your device."
      action={
        <button type="button" onClick={handleCreate} className="btn btn-primary">
          <Plus size={16} />
          Create Path
        </button>
      }
    >
      <StatusBoard status={runtime} />

      {filtered.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title={paths.length === 0 ? "No Paths yet" : "No matches"}
          action={
            paths.length === 0 ? (
              <button type="button" onClick={handleCreate} className="btn btn-accent">
                Create your first Path
              </button>
            ) : undefined
          }
        >
          {paths.length === 0
            ? "A Path is made of Steps. Each Step has a When and a Then. Create one to begin."
            : "Try a different search term."}
        </EmptyState>
      ) : (
        <div className="script-grid">
          {filtered.map((path) => {
            const stepCount = path.steps.filter((r) => !isPlaceholderRule(r)).length;
            const readiness = getPathReadiness(path);
            const readinessVariant =
              readiness === "ready" ? "success" : readiness === "needs-setup" ? "warn" : "muted";

            return (
              <article key={path.id} className={`script-card script-card-${readiness}`}>
                <button type="button" onClick={() => openPath(path.id)} className="script-card-open">
                  <div className="script-card-top">
                    <div className="script-card-icon">
                      <GitBranch />
                    </div>
                    <div className="script-card-badges">
                      <Badge variant={readinessVariant}>{READINESS_LABEL[readiness]}</Badge>
                      {isBundledScript(bundledScripts, path.id) && <Badge variant="accent">Example</Badge>}
                    </div>
                  </div>
                  <h3 className="script-card-name">{scriptDisplayName(path)}</h3>
                  <p className="script-card-desc">{path.setup.description || "No description"}</p>
                  <div className="script-card-stats">
                    <span className="stat-pill">
                      {stepCount} step{stepCount !== 1 ? "s" : ""}
                    </span>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveId(path.id);
                    onNavigate({ category: "run", scriptId: path.id });
                  }}
                  className="script-card-run"
                >
                  <Phone />
                  Run
                </button>
              </article>
            );
          })}
        </div>
      )}
    </PageLayout>
  );
}
