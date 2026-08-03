import type { ReactNode } from 'react';
import { cn } from '@/utils/cn';

interface PanelProps {
  children: ReactNode;
  className?: string;
}

/**
 * The base surface every piece of content sits on.
 *
 * A single panel component keeps elevation, radius and border colour
 * consistent, so the interface reads as one system rather than a
 * collection of separately-styled boxes.
 */
export function Panel({ children, className }: PanelProps) {
  return (
    <section
      className={cn(
        'rounded-xl border border-surface-700/70 bg-surface-850/80 shadow-panel backdrop-blur-sm',
        className,
      )}
    >
      {children}
    </section>
  );
}

interface PanelHeaderProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

/** Standard panel heading with optional icon and trailing actions. */
export function PanelHeader({
  title,
  description,
  icon,
  actions,
  className,
}: PanelHeaderProps) {
  return (
    <header
      className={cn(
        'flex items-start justify-between gap-4 border-b border-surface-700/70 px-5 py-4',
        className,
      )}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-surface-700 bg-surface-800 text-accent">
            {icon}
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold tracking-wide text-content-primary">
            {title}
          </h2>
          {description ? (
            <p className="mt-0.5 text-xs text-content-muted">{description}</p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}

/** Padded body region for panel content. */
export function PanelBody({ children, className }: PanelProps) {
  return <div className={cn('p-5', className)}>{children}</div>;
}
