import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  GitBranch,
  Home,
  Library,
  Monitor,
  Pencil,
  Play,
  Radio,
  Search,
  Settings,
  Shield,
  Upload,
} from "lucide-react";
import { useScriptStore } from "@/store/ScriptStore";
import { getActiveScript } from "@/script/selectors";
import { scriptDisplayName } from "@/script/storage";
import { normalizeScript } from "@/script/compile";
import type { AppView } from "@/navigation";
import { loadRunHistory, subscribeRunHistory } from "@/history/runHistory";
import { isTauriApp } from "@/transport/createAppTransport";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface AppSidebarProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
}

export function AppSidebar({ view, onNavigate }: AppSidebarProps) {
  const { bundledScripts, customScripts, activeId, setActiveId, importScript } =
    useScriptStore();
  const importRef = useRef<HTMLInputElement>(null);
  const [failedCount, setFailedCount] = useState(
    () => loadRunHistory().filter((r) => r.outcome === "failed").length
  );
  const [apiOk, setApiOk] = useState(false);

  useEffect(() => {
    return subscribeRunHistory(() => {
      setFailedCount(loadRunHistory().filter((r) => r.outcome === "failed").length);
    });
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const res = await fetch("/api/health");
        if (!cancelled) setApiOk(res.ok);
      } catch {
        if (!cancelled) setApiOk(false);
      }
    };
    void tick();
    const id = window.setInterval(() => void tick(), 15000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const openPath = activeId
    ? getActiveScript(bundledScripts, customScripts, activeId)
    : undefined;

  const desktop = isTauriApp();
  const showTemplates = bundledScripts.length > 0;
  const showIssues = failedCount > 0;

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              isActive={view.category === "dashboard"}
              onClick={() => onNavigate({ category: "dashboard" })}
            >
              <Radio className="size-4" />
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">PromptPath</span>
                <span className="truncate text-xs text-muted-foreground">
                  {desktop ? "Desktop" : "Browser"} · Local
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <div className="px-2 group-data-[collapsible=icon]:hidden">
          <Badge variant={apiOk ? "secondary" : "destructive"} className="w-full justify-center">
            {apiOk ? "Connected" : "API offline"}
          </Badge>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workflows</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={view.category === "dashboard"}
                  onClick={() => onNavigate({ category: "dashboard" })}
                  tooltip="Dashboard"
                >
                  <Home />
                  <span>Dashboard</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={view.category === "workflows"}
                  onClick={() => onNavigate({ category: "workflows" })}
                  tooltip="Workflows"
                >
                  <GitBranch />
                  <span>Workflows</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={view.category === "runs"}
                  onClick={() => onNavigate({ category: "runs" })}
                  tooltip="Runs"
                >
                  <Play />
                  <span>Runs</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              {showTemplates && (
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={view.category === "templates"}
                    onClick={() => onNavigate({ category: "templates" })}
                    tooltip="Templates"
                  >
                    <Library />
                    <span>Templates</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Operations</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={view.category === "system"}
                  onClick={() => onNavigate({ category: "system" })}
                  tooltip="System"
                >
                  <Monitor />
                  <span>System</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              {showIssues && (
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={view.category === "runs"}
                    onClick={() => onNavigate({ category: "runs" })}
                    tooltip="Issues"
                  >
                    <AlertTriangle />
                    <span>Issues</span>
                    <SidebarMenuBadge>{failedCount}</SidebarMenuBadge>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Resources</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={view.category === "vault"}
                  onClick={() => onNavigate({ category: "vault" })}
                  tooltip="Vault"
                >
                  <Shield />
                  <span>Vault</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton onClick={() => importRef.current?.click()} tooltip="Import Path">
                  <Upload />
                  <span>Import</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {openPath && (view.category === "edit" || view.category === "run") && (
          <SidebarGroup>
            <SidebarGroupLabel>{scriptDisplayName(openPath)}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={view.category === "edit"}
                    onClick={() => onNavigate({ category: "edit", scriptId: activeId })}
                    tooltip="Edit Path"
                  >
                    <Pencil />
                    <span>Edit Path</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={view.category === "run"}
                    onClick={() => onNavigate({ category: "run", scriptId: activeId })}
                    tooltip="Run Path"
                  >
                    <Play />
                    <span>Run Path</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              isActive={view.category === "settings"}
              onClick={() => onNavigate({ category: "settings" })}
              tooltip="Settings"
            >
              <Settings />
              <span>Settings</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <input
          ref={importRef}
          type="file"
          accept="application/json"
          hidden
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            try {
              const raw = JSON.parse(await file.text());
              const next = normalizeScript(raw);
              importScript(raw);
              setActiveId(next.id);
              onNavigate({ category: "edit", scriptId: next.id });
            } catch {
              alert("Invalid Path file");
            }
            e.target.value = "";
          }}
        />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

interface ShellHeaderProps {
  view: AppView;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export function ShellHeader({ view, searchQuery, onSearchChange }: ShellHeaderProps) {
  if (view.category !== "workflows") return null;

  return (
    <div className="shell-topbar flex items-center gap-2 border-b px-4 py-2">
      <Search className="size-4 shrink-0 text-muted-foreground" />
      <Input
        type="search"
        placeholder="Search workflows…"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        className="max-w-sm border-0 bg-transparent shadow-none focus-visible:ring-0"
      />
    </div>
  );
}
