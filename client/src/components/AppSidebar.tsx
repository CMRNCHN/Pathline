import {
  GitBranch,
  Home,
  Monitor,
  Shield,
  Users,
} from "lucide-react";
import type { AppView } from "@/navigation";
import { isPrimaryNav } from "@/navigation";
import { fetchHealth } from "@/api";
import { isTauriApp } from "@/transport/createAppTransport";
import { useEffect, useState } from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { Radio } from "lucide-react";

interface AppSidebarProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
}

const NAV: { category: AppView["category"]; label: string; icon: typeof Home }[] = [
  { category: "dashboard", label: "Dashboard", icon: Home },
  { category: "paths", label: "Path Library", icon: GitBranch },
  { category: "accounts", label: "Accounts", icon: Users },
  { category: "vault", label: "Input Vault", icon: Shield },
  { category: "system", label: "System", icon: Monitor },
];

export function AppSidebar({ view, onNavigate }: AppSidebarProps) {
  const [apiOk, setApiOk] = useState(false);
  const desktop = isTauriApp();

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        await fetchHealth();
        if (!cancelled) setApiOk(true);
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

  return (
    <Sidebar collapsible="none">
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
                <span className="truncate font-semibold">Pathline</span>
                <span className="truncate text-xs text-muted-foreground">
                  {desktop ? "Desktop" : "Local"} · Five surfaces
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <div className="px-2">
          <Badge variant={apiOk ? "secondary" : "destructive"} className="w-full justify-center">
            {apiOk ? "Connected" : "API offline"}
          </Badge>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigate</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV.map(({ category, label, icon: Icon }) => (
                <SidebarMenuItem key={category}>
                  <SidebarMenuButton
                    isActive={isPrimaryNav(view, category)}
                    onClick={() => {
                      if (category === "dashboard") onNavigate({ category: "dashboard" });
                      else if (category === "paths") onNavigate({ category: "paths" });
                      else if (category === "accounts") onNavigate({ category: "accounts" });
                      else if (category === "vault") onNavigate({ category: "vault" });
                      else onNavigate({ category: "system" });
                    }}
                    tooltip={label}
                  >
                    <Icon />
                    <span>{label}</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}

/** Optional Path Library search strip — kept for Shell compatibility. */
export function ShellHeader({
  view,
  searchQuery,
  onSearchChange,
}: {
  view: AppView;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}) {
  void view;
  void searchQuery;
  void onSearchChange;
  return null;
}
