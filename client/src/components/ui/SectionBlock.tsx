import type { ReactNode } from "react";

interface SectionBlockProps {
  index: string;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  wide?: boolean;
  /** Large inline title — e.g. editable script name on Setup. */
  heroTitle?: ReactNode;
  actions?: ReactNode;
}

export function SectionBlock({
  index,
  title,
  description,
  children,
  wide,
  heroTitle,
  actions,
}: SectionBlockProps) {
  return (
    <section className={`section-block${wide ? " section-block-wide" : ""}`}>
      <header className="section-block-header">
        <div className="section-block-heading">
          <div className="section-title-row">
            <p className={`section-step-label${heroTitle ? "" : " section-step-label-prominent"}`}>
              <span className="section-step-index">{index}</span>
              {title}
            </p>
            {heroTitle && <div className="section-hero-title">{heroTitle}</div>}
          </div>
          {description && <p className="section-desc">{description}</p>}
        </div>
        {actions && <div className="section-block-actions">{actions}</div>}
      </header>
      <div className="section-block-body">{children}</div>
    </section>
  );
}
