import type { ReactNode } from "react";

interface PageShellProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}

export function PageShell({ title, subtitle, action, children, wide }: PageShellProps) {
  return (
    <div className={`p-8 mx-auto space-y-8 ${wide ? "max-w-6xl" : "max-w-5xl"}`}>
      <header className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{title}</h1>
          {subtitle && <p className="text-sm text-muted mt-1">{subtitle}</p>}
        </div>
        {action}
      </header>
      {children}
    </div>
  );
}
