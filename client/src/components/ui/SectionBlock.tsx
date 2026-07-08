import type { ReactNode } from "react";

interface SectionBlockProps {
  index: string;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}

export function SectionBlock({ index, title, description, children, wide }: SectionBlockProps) {
  return (
    <section className={`section-block${wide ? " section-block-wide" : ""}`}>
      <header className="section-block-header">
        <span className="section-index">{index}</span>
        <div>
          <h2 className="section-title">{title}</h2>
          {description && <p className="section-desc">{description}</p>}
        </div>
      </header>
      <div className="section-block-body">{children}</div>
    </section>
  );
}
