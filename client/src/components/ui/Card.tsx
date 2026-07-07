import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  children: ReactNode;
  className?: string;
}

export function Card({ title, children, className = "" }: CardProps) {
  return (
    <section className={`bg-white border border-[#0a0a0b14] rounded-xl p-6 shadow-sm ${className}`}>
      {title && <h3 className="font-semibold text-ink mb-4">{title}</h3>}
      {children}
    </section>
  );
}
