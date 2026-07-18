export type AppView =
  | { category: "dashboard" }
  | { category: "workflows" }
  | { category: "runs" }
  | { category: "templates" }
  | { category: "system" }
  | { category: "vault" }
  | { category: "settings" }
  | { category: "edit"; scriptId: string }
  | { category: "run"; scriptId: string };

/** Labels for the shell breadcrumb strip. */
export function viewLabel(view: AppView): string {
  switch (view.category) {
    case "dashboard":
      return "Dashboard";
    case "workflows":
      return "Workflows";
    case "runs":
      return "Runs";
    case "templates":
      return "Templates";
    case "system":
      return "System";
    case "vault":
      return "Vault";
    case "settings":
      return "Settings";
    case "edit":
      return "Edit Workflow";
    case "run":
      return "Run";
  }
}

export function isPrimaryNav(view: AppView, category: AppView["category"]): boolean {
  return view.category === category;
}
