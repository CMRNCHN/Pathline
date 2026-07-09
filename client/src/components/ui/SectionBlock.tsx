import type { ReactNode } from "react";

interface SectionBlockProps {
  index: string;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  wide?: boolean;
  /** Replaces the default section title — e.g. editable script name in Setup. */
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
        <span className="section-index">{index}</span>
        <div className="section-block-heading">
          {heroTitle ? (
            <>
              {heroTitle}
              <p className="section-desc">
                <span className="section-kicker">{title}</span>
                {description && (
                  <>
                    <span className="section-desc-sep"> · </span>
                    {description}
                  </>
                )}
              </p>
            </>
          ) : (
            <>
              <h2 className="section-title">{title}</h2>
              {description && <p className="section-desc">{description}</p>}
            </>
          )}
        </div>
        {actions && <div className="section-block-actions">{actions}</div>}
      </header>
      <div className="section-block-body">{children}</div>
    </section>
  );
}
