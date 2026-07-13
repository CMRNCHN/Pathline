import type { ElementType, ReactNode } from "react";

interface SectionCardProps {
  title?: string;
  icon?: ElementType;
  children: ReactNode;
  className?: string;
  variant?: "default" | "dark";
}

/** Legacy settings section card — migrate to shadcn Card over time. */
export function SectionCard({
  title,
  icon: Icon,
  children,
  className = "",
  variant = "default",
}: SectionCardProps) {
  return (
    <section className={`card card-${variant} ${className}`.trim()}>
      {(title || Icon) && (
        <header className="card-header">
          {Icon && (
            <span className="card-icon">
              <Icon aria-hidden />
            </span>
          )}
          {title && <h3 className="card-title">{title}</h3>}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}
