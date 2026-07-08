import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function PageHeader({ eyebrow, title, subtitle, action }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        {eyebrow && <p className="page-eyebrow">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {action && <div className="page-header-action">{action}</div>}
    </header>
  );
}

interface PageLayoutProps extends PageHeaderProps {
  children: ReactNode;
  wide?: boolean;
  flush?: boolean;
}

export function PageLayout({
  eyebrow,
  title,
  subtitle,
  action,
  wide,
  flush,
  children,
}: PageLayoutProps) {
  return (
    <div className={`page${wide ? " page-wide" : ""}${flush ? " page-flush" : ""}`}>
      <PageHeader eyebrow={eyebrow} title={title} subtitle={subtitle} action={action} />
      <div className="page-body">{children}</div>
    </div>
  );
}
