export type AppView =
  | { category: "paths" }
  | { category: "edit"; scriptId: string }
  | { category: "run"; scriptId: string }
  | { category: "history" }
  | { category: "settings" };
