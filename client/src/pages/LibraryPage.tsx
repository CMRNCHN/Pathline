import { useMemo } from "react";
import { FileText, Phone, Plus } from "lucide-react";
import { CallStateBoard } from "../components/CallStateBoard";
import { DEMO_ACTIVE_CALLSTATE, MEDICARE_PATH } from "../callstate";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript, mergeScripts } from "../script/selectors";
import { PageLayout } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { Badge } from "../components/ui/Badge";
import { scriptDisplayName } from "../script/storage";
import { getScriptReadiness, READINESS_LABEL } from "../script/scriptReadiness";
import type { AppView } from "../navigation";

interface LibraryPageProps {
  onNavigate: (view: AppView) => void;
  searchQuery: string;
}

export function LibraryPage({ onNavigate, searchQuery }: LibraryPageProps) {
  const { bundledScripts, customScripts, setActiveId, addCustom, loading, error } =
    useScriptStore();

  const scripts = mergeScripts(bundledScripts, customScripts);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return scripts;
    const q = searchQuery.toLowerCase();
    return scripts.filter(
      (s) =>
        s.setup.name.toLowerCase().includes(q) ||
        s.setup.description.toLowerCase().includes(q)
    );
  }, [scripts, searchQuery]);

  const openScript = (id: string) => {
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
      eyebrow="Dashboard"
      title="Scripts"
      subtitle="Event-sourced callstate projections — open a card to edit Setup, Steps, and Results."
      action={
        <button type="button" onClick={handleCreate} className="btn btn-primary">
          <Plus size={16} />
          New script
        </button>
      }
    >
      <CallStateBoard callState={DEMO_ACTIVE_CALLSTATE} path={MEDICARE_PATH} />

      {filtered.length === 0 ? (
        <EmptyState
          icon={FileText}
          title={scripts.length === 0 ? "No scripts yet" : "No matches"}
          action={
            scripts.length === 0 ? (
              <button type="button" onClick={handleCreate} className="btn btn-accent">
                Create your first script
              </button>
            ) : undefined
          }
        >
          {scripts.length === 0
            ? "Each RUN template has Setup, Rules, and Results — outputs are defined on rules."
            : "Try a different search term."}
        </EmptyState>
      ) : (
        <div className="script-grid">
          {filtered.map((script) => {
            const readiness = getScriptReadiness(script);
            const readinessVariant =
              readiness === "ready" ? "success" : readiness === "needs-setup" ? "warn" : "muted";

            return (
              <article key={script.id} className={`script-card script-card-${readiness}`}>
                <button type="button" onClick={() => openScript(script.id)} className="script-card-open">
                  <div className="script-card-top">
                    <div className="script-card-icon">
                      <FileText />
                    </div>
                    <div className="script-card-badges">
                      <Badge variant={readinessVariant}>{READINESS_LABEL[readiness]}</Badge>
                      {isBundledScript(bundledScripts, script.id) && (
                        <Badge variant="accent">Example</Badge>
                      )}
                    </div>
                  </div>
                  <h3 className="script-card-name">{scriptDisplayName(script)}</h3>
                  <p className="script-card-desc">
                    {script.setup.description || "No description"}
                  </p>
                  <div className="script-card-stats">
                    <span className="stat-pill">{script.ivrRules.length} rules</span>
                    <span className="stat-pill">
                      {script.ivrRules.filter((r) => r.output.trim()).length} outputs
                    </span>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveId(script.id);
                    onNavigate({ category: "run", scriptId: script.id });
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

      {(loading || error) && (
        <p className="field-hint" style={{ marginTop: "1rem" }}>
          {loading ? "Loading scripts…" : error}
        </p>
      )}
    </PageLayout>
  );
}
