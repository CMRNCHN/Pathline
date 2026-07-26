import {
  GitBranch,
  Home,
  Monitor,
  Users,
  Radio,
  Moon,
  Sun,
} from "lucide-react";
import type { AppView } from "@/navigation";
import { isPrimaryNav } from "@/navigation";
import { fetchHealth } from "@/api";
import { isTauriApp } from "@/transport/createAppTransport";
import { useEffect, useState } from "react";
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
} from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";

interface AppSidebarProps {
  view: AppView;
  onNavigate: (view: AppView) => void;
}

const NAV: { category: AppView["category"]; label: string; icon: typeof Home }[] = [
  { category: "dashboard", label: "Dashboard", icon: Home },
  { category: "paths", label: "Path Library", icon: GitBranch },
  { category: "accounts", label: "Accounts", icon: Users },
  { category: "system", label: "System", icon: Monitor },
];

function useThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof document === "undefined") return "light";
    const saved = window.localStorage.getItem("pathline-theme");
    if (saved === "dark" || saved === "light") return saved;
    return document.documentElement.classList.contains("dark") ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.setAttribute("data-theme", theme);
    window.localStorage.setItem("pathline-theme", theme);
  }, [theme]);

  return {
    theme,
    toggle: () => setTheme((t) => (t === "light" ? "dark" : "light")),
  };
}

export function AppSidebar({ view, onNavigate }: AppSidebarProps) {
  const [apiOk, setApiOk] = useState(false);
  const desktop = isTauriApp();
  const { theme, toggle } = useThemeToggle();

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
                  {desktop ? "Desktop" : "Local"}
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

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton type="button" onClick={toggle} tooltip="Toggle theme">
              {theme === "light" ? <Moon /> : <Sun />}
              <span>{theme === "light" ? "Dark mode" : "Light mode"}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
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
