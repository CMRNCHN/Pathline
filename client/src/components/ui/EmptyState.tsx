import type { ElementType, ReactNode } from "react";
import { Card, CardContent } from "@/components/ui/card";

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
    <Card className="border-dashed py-0 shadow-none">
      <CardContent className="flex flex-col items-center px-8 py-14 text-center">
        <div className="mb-4 inline-flex size-14 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <Icon aria-hidden className="size-6" />
        </div>
        <h3 className="text-base font-semibold">{title}</h3>
        <p className="mt-1.5 text-sm text-muted-foreground">{children}</p>
        {action && <div className="mt-5">{action}</div>}
      </CardContent>
    </Card>
  );
}
