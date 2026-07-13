import type { ReactNode } from "react";

type PathBadgeVariant = "default" | "accent" | "success" | "warn" | "muted";

const variantClass: Record<PathBadgeVariant, string> = {
  default: "badge",
  accent: "badge badge-accent",
  success: "badge badge-success",
  warn: "badge badge-warn",
  muted: "badge badge-muted",
};

/** Legacy path readiness badge — migrate to shadcn Badge over time. */
export function PathBadge({
  children,
  variant = "default",
}: {
  children: ReactNode;
  variant?: PathBadgeVariant;
}) {
  return <span className={variantClass[variant]}>{children}</span>;
}
