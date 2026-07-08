import type { ElementType, ReactNode } from "react";

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: ElementType;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">
        <Icon aria-hidden />
      </div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-text">{children}</p>
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}
