import { useMemo } from "react";
import { GitBranch, Phone, Plus } from "lucide-react";
import { StatusBoard } from "../components/StatusBoard";
import { useRuntimeStatus } from "../hooks/useRuntimeStatus";
import { useScriptStore } from "../store/ScriptStore";
import { isBundledScript, mergeScripts } from "../script/selectors";
import { PageLayout } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/EmptyState";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { scriptDisplayName } from "../script/storage";
import { isPlaceholderRule } from "../script/ruleIntent";
import { getPathReadiness, READINESS_LABEL } from "../script/pathReadiness";
import type { AppView } from "../navigation";

interface PathsPageProps {
  onNavigate: (view: AppView) => void;
  searchQuery: string;
}

function readinessBadgeVariant(readiness: ReturnType<typeof getPathReadiness>) {
  if (readiness === "ready") return "default" as const;
  if (readiness === "needs-setup") return "secondary" as const;
  return "outline" as const;
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
        <Button type="button" onClick={handleCreate}>
          <Plus size={16} />
          Create Path
        </Button>
      }
    >
      <StatusBoard status={runtime} />

      {filtered.length === 0 ? (
        <EmptyState
          icon={GitBranch}
          title={paths.length === 0 ? "No Paths yet" : "No matches"}
          action={
            paths.length === 0 ? (
              <Button type="button" onClick={handleCreate}>
                Create your first Path
              </Button>
            ) : undefined
          }
        >
          {paths.length === 0
            ? "A Path is made of Steps. Each Step has a When and a Then. Create one to begin."
            : "Try a different search term."}
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((path) => {
            const stepCount = path.steps.filter((r) => !isPlaceholderRule(r)).length;
            const readiness = getPathReadiness(path);

            return (
              <Card key={path.id} className="flex flex-col">
                <button
                  type="button"
                  onClick={() => openPath(path.id)}
                  className="flex flex-1 flex-col text-left outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-xl"
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <GitBranch className="size-4" />
                      </div>
                      <div className="flex flex-wrap justify-end gap-1">
                        <Badge variant={readinessBadgeVariant(readiness)}>
                          {READINESS_LABEL[readiness]}
                        </Badge>
                        {isBundledScript(bundledScripts, path.id) && (
                          <Badge variant="outline">Example</Badge>
                        )}
                      </div>
                    </div>
                    <CardTitle className="mt-2">{scriptDisplayName(path)}</CardTitle>
                    <CardDescription>
                      {path.setup.description || "No description"}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <Badge variant="secondary">
                      {stepCount} step{stepCount !== 1 ? "s" : ""}
                    </Badge>
                  </CardContent>
                </button>
                <CardFooter className="border-t">
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => {
                      setActiveId(path.id);
                      onNavigate({ category: "run", scriptId: path.id });
                    }}
                  >
                    <Phone />
                    Run
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}
    </PageLayout>
  );
}
