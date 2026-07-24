import { Plus } from "lucide-react";
import { PathListItem } from "./PathListItem";
import type { PathDocument } from "@/script/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/EmptyState";
import { GitBranch } from "lucide-react";

interface PathListProps {
  paths: PathDocument[];
  selectedId?: string;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

export function PathList({
  paths,
  selectedId,
  searchQuery,
  onSearchChange,
  onSelect,
  onCreate,
}: PathListProps) {
  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex gap-2">
        <Input
          type="search"
          placeholder="Search paths…"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="h-9"
          aria-label="Search paths"
        />
        <Button type="button" size="sm" onClick={onCreate} className="shrink-0">
          <Plus className="size-4" />
          New
        </Button>
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {paths.length === 0 ? (
          <EmptyState icon={GitBranch} title="No paths yet">
            Create a Path to build a call script.
          </EmptyState>
        ) : (
          paths.map((path) => (
            <PathListItem
              key={path.id}
              path={path}
              selected={selectedId === path.id}
              onSelect={() => onSelect(path.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
