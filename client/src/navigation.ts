export type AppView =
  | { category: "dashboard" }
  | { category: "paths"; pathId?: string; panel?: "edit" | "run" }
  | { category: "accounts"; accountId?: string; panel?: "profile" | "secrets" }
  | { category: "system" };

/** Labels for the shell breadcrumb strip. */
export function viewLabel(view: AppView): string {
  switch (view.category) {
    case "dashboard":
      return "Dashboard";
    case "paths":
      return "Path Library";
    case "accounts":
      return "Accounts";
    case "system":
      return "System";
  }
}

export function isPrimaryNav(view: AppView, category: AppView["category"]): boolean {
  return view.category === category;
}
