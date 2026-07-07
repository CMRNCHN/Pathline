import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  wide?: boolean;
}

export function PageHeader({ title, subtitle, action, wide }: PageHeaderProps) {
  return (
    <header className={`flex items-center justify-between gap-4 flex-wrap ${wide ? "" : ""}`}>
      <div>
        <h1 className="text-2xl font-semibold text-ink">{title}</h1>
        {subtitle && <p className="text-sm text-muted mt-1">{subtitle}</p>}
      </div>
      {action}
    </header>
  );
}

interface PageLayoutProps extends PageHeaderProps {
  children: ReactNode;
}

export function PageLayout({ title, subtitle, action, wide, children }: PageLayoutProps) {
  return (
    <div className={`p-8 mx-auto space-y-8 ${wide ? "max-w-6xl" : "max-w-5xl"}`}>
      <PageHeader title={title} subtitle={subtitle} action={action} wide={wide} />
      {children}
    </div>
  );
}
