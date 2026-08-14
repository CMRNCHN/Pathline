import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CopyButtonProps {
  /** Text to put on the clipboard. Empty disables the control. */
  value: string;
  label?: string;
  className?: string;
  size?: "sm" | "icon-sm" | "icon";
}

async function writeClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/** One-click copy. Does not log or echo the value. */
export function CopyButton({
  value,
  label = "Copy",
  className,
  size = "icon-sm",
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const disabled = !value;

  return (
    <Button
      type="button"
      variant="ghost"
      size={size}
      className={cn("shrink-0 text-muted-foreground hover:text-foreground", className)}
      disabled={disabled}
      aria-label={copied ? "Copied" : label}
      title={copied ? "Copied" : label}
      onClick={() => {
        if (!value) return;
        void writeClipboard(value).then((ok) => {
          if (!ok) return;
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1200);
        });
      }}
    >
      {copied ? <Check className="size-3.5 text-primary" /> : <Copy className="size-3.5" />}
    </Button>
  );
}
