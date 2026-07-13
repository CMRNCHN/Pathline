import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function PageHeader({ eyebrow, title, subtitle, action }: PageHeaderProps) {
  return (
    <header className="mb-8 flex flex-wrap items-start justify-between gap-6">
      <div className="min-w-0">
        {eyebrow && (
          <p className="mb-1.5 text-[0.6875rem] font-semibold uppercase tracking-wider text-primary">
            {eyebrow}
          </p>
        )}
        <h1 className="text-[1.75rem] font-bold leading-tight tracking-tight">{title}</h1>
        {subtitle && (
          <p className="mt-2 max-w-xl text-[0.9375rem] text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
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
    <div
      className={cn(
        "mx-auto animate-in px-6 pt-8 pb-12 duration-350 fade-in slide-in-from-bottom-1.5",
        wide ? "max-w-6xl" : "max-w-4xl",
        flush && "max-w-none p-0"
      )}
    >
      <PageHeader eyebrow={eyebrow} title={title} subtitle={subtitle} action={action} />
      <div className="flex flex-col gap-6">{children}</div>
    </div>
  );
}
