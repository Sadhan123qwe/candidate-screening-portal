import type { ReactNode } from "react";

interface PageHeaderProps {
  title: ReactNode;
  subtitle?: ReactNode;
  /** Right-aligned, level with the bottom of the title block. */
  aside?: ReactNode;
}

export function PageHeader({ title, subtitle, aside }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="min-w-0">
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {aside}
    </header>
  );
}
