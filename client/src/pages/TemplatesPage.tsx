import { useMemo } from "react";
import { Library, Pencil } from "lucide-react";
import { PageLayout } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { AppView } from "@/navigation";
import { isPlaceholderRule } from "@/script/ruleIntent";
import { scriptDisplayName } from "@/script/storage";
import { useScriptStore } from "@/store/ScriptStore";

interface TemplatesPageProps {
  onNavigate: (view: AppView) => void;
}

export function TemplatesPage({ onNavigate }: TemplatesPageProps) {
  const { bundledScripts, setActiveId } = useScriptStore();

  const templates = useMemo(() => bundledScripts, [bundledScripts]);

  return (
    <PageLayout
      title="Templates"
      subtitle="Starter Paths you can clone into your library. Templates never store your Inputs."
    >
      {templates.length === 0 ? (
        <EmptyState icon={Library} title="No templates yet">
          Example Paths will appear here when bundled templates are available.
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {templates.map((path) => {
            const steps = path.steps.filter((r) => !isPlaceholderRule(r)).length;
            return (
              <Card key={path.id} className="flex flex-col">
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle>{scriptDisplayName(path)}</CardTitle>
                    <Badge variant="outline">Example</Badge>
                  </div>
                  <CardDescription>
                    {path.setup.description || "No description"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Badge variant="secondary">
                    {steps} step{steps !== 1 ? "s" : ""}
                  </Badge>
                </CardContent>
                <CardFooter className="border-t gap-2">
                  <Button
                    type="button"
                    className="w-full"
                    onClick={() => {
                      setActiveId(path.id);
                      onNavigate({ category: "edit", scriptId: path.id });
                    }}
                  >
                    <Pencil className="size-4" />
                    Open Path
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
