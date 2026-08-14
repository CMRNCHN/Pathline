import { getPathReadiness, READINESS_LABEL } from "@/script/pathReadiness";
import { scriptDisplayName } from "@/script/storage";
import { isPlaceholderRule } from "@/script/ruleIntent";
import type { PathDocument } from "@/script/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

function readinessVariant(readiness: ReturnType<typeof getPathReadiness>) {
  if (readiness === "ready") return "default" as const;
  if (readiness === "needs-setup") return "secondary" as const;
  return "outline" as const;
}

interface PathListItemProps {
  path: PathDocument;
  selected: boolean;
  onSelect: () => void;
}

export function PathListItem({ path, selected, onSelect }: PathListItemProps) {
  const readiness = getPathReadiness(path);
  const steps = path.steps.filter((s) => !isPlaceholderRule(s)).length;

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-2 rounded-md border px-2.5 py-1.5 text-left transition-colors",
        selected ? "border-primary bg-primary/5" : "hover:bg-muted/60"
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="min-w-0 truncate text-sm font-medium">{scriptDisplayName(path)}</span>
          <Badge variant={readinessVariant(readiness)} className="shrink-0 text-[10px]">
            {READINESS_LABEL[readiness]}
          </Badge>
        </div>
        <p className="truncate text-[11px] text-muted-foreground">
          {path.setup.target
            ? `${path.setup.target} · ${steps} step${steps === 1 ? "" : "s"}`
            : path.setup.description || `${steps} step${steps === 1 ? "" : "s"}`}
        </p>
      </div>
    </button>
  );
}
