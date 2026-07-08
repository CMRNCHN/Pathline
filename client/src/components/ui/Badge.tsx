import type { ReactNode } from "react";

type BadgeVariant = "default" | "accent" | "success" | "muted";

const variantClass: Record<BadgeVariant, string> = {
  default: "badge",
  accent: "badge badge-accent",
  success: "badge badge-success",
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
