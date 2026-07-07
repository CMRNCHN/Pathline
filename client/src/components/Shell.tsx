import type { ReactNode } from "react";
import type { AppView } from "../navigation";
import { TopNav } from "./TopNav";

interface ShellProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  children: ReactNode;
}

export function Shell({ view, onNavigate, searchQuery, onSearchChange, children }: ShellProps) {
  return (
    <div className="flex flex-col h-screen w-full bg-canvas font-sans text-ink overflow-hidden">
      <TopNav
        view={view}
        onNavigate={onNavigate}
        searchQuery={searchQuery}
        onSearchChange={onSearchChange}
      />
      <main className="flex-1 overflow-y-auto bg-canvas min-w-0">{children}</main>
    </div>
  );
}
