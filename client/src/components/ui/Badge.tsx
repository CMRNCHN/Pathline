import type { ReactNode } from "react";

type BadgeVariant = "default" | "accent" | "success" | "warn" | "muted";

const variantClass: Record<BadgeVariant, string> = {
  default: "badge",
  accent: "badge badge-accent",
  success: "badge badge-success",
  warn: "badge badge-warn",
  muted: "badge badge-muted",
};

export function Badge({
  children,
  variant = "default",
}: {
  children: ReactNode;
  variant?: BadgeVariant;
}) {
  return <span className={variantClass[variant]}>{children}</span>;
}
