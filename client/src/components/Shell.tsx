import type { ReactNode } from "react";
import type { AppView } from "../navigation";
import { AppSidebar, ShellHeader } from "./AppSidebar";
import { ThemeToggle } from "./ThemeToggle";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "./ui/sidebar";
import { Separator } from "./ui/separator";

interface ShellProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  children: ReactNode;
}

export function Shell({
  view,
  onNavigate,
  searchQuery,
  onSearchChange,
  children,
}: ShellProps) {
  return (
    <SidebarProvider>
      <AppSidebar view={view} onNavigate={onNavigate} />
      <SidebarInset>
        <header className="flex h-12 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="md:hidden" />
          <Separator orientation="vertical" className="mr-2 hidden h-4 md:block" />
          <span className="min-w-0 truncate text-sm font-medium text-muted-foreground">
            {view.category === "paths" && "Paths"}
            {view.category === "history" && "History"}
            {view.category === "settings" && "Settings"}
            {view.category === "edit" && "Edit Path"}
            {view.category === "run" && "Run Path"}
          </span>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>
        <ShellHeader
          view={view}
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
        />
        <div className="flex-1 overflow-y-auto app-main min-w-0">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
