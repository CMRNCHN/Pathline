import { Check } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type RunStep = "consent" | "configure" | "active";

const STEPS: { id: RunStep; label: string }[] = [
  { id: "consent", label: "Consent" },
  { id: "configure", label: "Inputs" },
  { id: "active", label: "Status" },
];

export function RunStepBar({ current }: { current: RunStep }) {
  const currentIdx = STEPS.findIndex((s) => s.id === current);

  return (
    <Card className="mb-6 overflow-x-auto py-4 shadow-none" size="sm">
      <nav className="flex items-center px-5" aria-label="Run progress">
        {STEPS.map((step, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          return (
            <div key={step.id} className="flex shrink-0 items-center">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "flex size-6 items-center justify-center rounded-full border-[1.5px] text-[0.6875rem] font-bold",
                    active && "border-primary bg-primary text-primary-foreground",
                    done && "border-emerald-600 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40",
                    !active && !done && "border-border bg-muted text-muted-foreground"
                  )}
                >
                  {done ? <Check className="size-3" strokeWidth={3} /> : i + 1}
                </span>
                <span
                  className={cn(
                    "text-[0.8125rem] font-medium text-muted-foreground",
                    active && "font-semibold text-foreground"
                  )}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <span className="mx-3 h-px w-8 bg-border" aria-hidden />
              )}
            </div>
          );
        })}
      </nav>
    </Card>
  );
}
