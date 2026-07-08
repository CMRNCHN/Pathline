import type { ElementType, ReactNode } from "react";

interface CardProps {
  title?: string;
  icon?: ElementType;
  children: ReactNode;
  className?: string;
  variant?: "default" | "dark";
}

export function Card({ title, icon: Icon, children, className = "", variant = "default" }: CardProps) {
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
