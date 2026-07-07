export type AppView =
  | { category: "library" }
  | { category: "edit"; scriptId: string }
  | { category: "run"; scriptId: string }
  | { category: "script-settings"; scriptId: string }
  | { category: "system" }
  | { category: "settings" };
