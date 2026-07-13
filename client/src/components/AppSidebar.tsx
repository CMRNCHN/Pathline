import { useRef } from "react";
import {
  Clock,
  GitBranch,
  Pencil,
  Play,
  Radio,
  Search,
  Settings,
  Upload,
} from "lucide-react";
import { useScriptStore } from "@/store/ScriptStore";
import { getActiveScript } from "@/script/selectors";
import { scriptDisplayName } from "@/script/storage";
import { normalizeScript } from "@/script/compile";
import type { AppView } from "@/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";

interface AppSidebarProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
}

export function AppSidebar({ view, onNavigate }: AppSidebarProps) {
  const { bundledScripts, customScripts, activeId, setActiveId, importScript } =
    useScriptStore();
  const importRef = useRef<HTMLInputElement>(null);

  const openPath = activeId
    ? getActiveScript(bundledScripts, customScripts, activeId)
    : undefined;

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              isActive={view.category === "paths"}
              onClick={() => onNavigate({ category: "paths" })}
            >
              <Radio className="size-4" />
              <span>Pathline</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigate</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={view.category === "paths"}
                  onClick={() => onNavigate({ category: "paths" })}
                  tooltip="Paths"
                >
                  <GitBranch />
                  <span>Paths</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  isActive={view.category === "history"}
                  onClick={() => onNavigate({ category: "history" })}
                  tooltip="History"
                >
                  <Clock />
                  <span>History</span>
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
                    tooltip="Edit"
                  >
                    <Pencil />
                    <span>Edit</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={view.category === "run"}
                    onClick={() => onNavigate({ category: "run", scriptId: activeId })}
                    tooltip="Run"
                  >
                    <Play />
                    <span>Run</span>
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
            <SidebarMenuButton onClick={() => importRef.current?.click()} tooltip="Import">
              <Upload />
              <span>Import</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
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
  if (view.category !== "paths") return null;

  return (
    <div className="flex items-center gap-2 border-b px-4 py-2">
      <Search className="size-4 shrink-0 text-muted-foreground" />
      <input
        type="text"
        placeholder="Search paths…"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        className="h-8 w-full max-w-sm bg-transparent text-sm outline-none placeholder:text-muted-foreground"
      />
    </div>
  );
}
