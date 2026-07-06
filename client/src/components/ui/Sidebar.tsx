import type { ElementType, ReactNode } from "react";

export function SidebarItem({
  icon: Icon,
  label,
  isActive,
  onClick,
  indent = 0,
}: {
  icon?: ElementType;
  label: string;
  isActive?: boolean;
  onClick?: () => void;
  indent?: number;
}) {
  return (
    <button
      onClick={onClick}
      style={{ paddingLeft: `${12 + indent * 10}px` }}
      className={`w-full flex items-center gap-3 pr-3 py-2 rounded-md text-sm transition-colors ${
        isActive
          ? "bg-surface text-white font-medium"
          : "text-[#a1a1aa] hover:bg-surface/50 hover:text-zinc-200"
      }`}
    >
      {Icon && <Icon className="w-4 h-4 shrink-0" />}
      <span className="truncate text-left">{label}</span>
    </button>
  );
}

export function SidebarSection({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section>
      <div className="text-[#71717a] text-xs font-bold uppercase tracking-wider px-3 mb-2 mt-4">
        {label}
      </div>
      {children}
    </section>
  );
}
