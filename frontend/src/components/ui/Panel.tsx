import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import { cn } from '@/utils/cn';

interface PanelProps extends ComponentPropsWithoutRef<'section'> {
  children: ReactNode;
  /** Raises the surface one step, for panels that sit on top of others. */
  raised?: boolean;
}

/**
 * The instrument housing every piece of content sits in.
 *
 * Square-ish corners and a hairline edge rather than a soft rounded
 * card: the reference is rack-mounted equipment, not a consumer app.
 * A single component keeps elevation and edge treatment identical
 * across the product, so the interface reads as one machine.
 */
export function Panel({ children, className, raised = false, ...rest }: PanelProps) {
  return (
    <section
      {...rest}
      className={cn(
        'relative rounded-panel border border-edge shadow-panel',
        raised ? 'bg-panel-raised' : 'bg-panel',
        className,
      )}
    >
      {children}
    </section>
  );
}

interface PanelHeaderProps {
  title: string;
  /** Short qualifier shown beneath the title. */
  subtitle?: string;
  icon?: ReactNode;
  /** Right-aligned controls or status chips. */
  actions?: ReactNode;
  /** Status rail colour class, e.g. from a tone's `rail`. */
  rail?: string;
  className?: string;
  /** Compact variant for dense panel stacks. */
  dense?: boolean;
}

/**
 * Panel header rail.
 *
 * The title is a small, wide-tracked uppercase label rather than a
 * heading — it names an instrument, and should recede once an operator
 * knows the layout, leaving the data as the loudest element.
 */
export function PanelHeader({
  title,
  subtitle,
  icon,
  actions,
  rail,
  className,
  dense = false,
}: PanelHeaderProps) {
  return (
    <header
      className={cn(
        'flex items-center justify-between gap-3 border-b border-edge bg-panel-rail/60',
        dense ? 'px-3 py-2' : 'px-4 py-2.5',
        rail,
        className,
      )}
    >
      <div className="flex min-w-0 items-center gap-2.5">
        {icon ? <span className="shrink-0 text-ink-faint">{icon}</span> : null}
        <div className="min-w-0">
          <h2 className="truncate text-2xs font-semibold uppercase tracking-[0.14em] text-ink-dim">
            {title}
          </h2>
          {subtitle ? (
            <p className="truncate text-2xs text-ink-ghost">{subtitle}</p>
          ) : null}
        </div>
      </div>
      {actions ? (
        <div className="flex shrink-0 items-center gap-1.5">{actions}</div>
      ) : null}
    </header>
  );
}

/** Padded body region. */
export function PanelBody({
  children,
  className,
  ...rest
}: ComponentPropsWithoutRef<'div'>) {
  return (
    <div {...rest} className={cn('p-4', className)}>
      {children}
    </div>
  );
}

/** Footer rail for summary figures or a link onward. */
export function PanelFooter({
  children,
  className,
  ...rest
}: ComponentPropsWithoutRef<'div'>) {
  return (
    <div
      {...rest}
      className={cn(
        'flex items-center justify-between gap-3 border-t border-edge bg-panel-rail/40 px-4 py-2',
        className,
      )}
    >
      {children}
    </div>
  );
}

/**
 * Section grouping header, used above a row of panels.
 *
 * Gives the dashboard an explicit reading order — sections are numbered
 * so an operator can be told "check section 3" over a radio.
 */
export function SectionHeading({
  index,
  title,
  hint,
  actions,
}: {
  index?: number;
  title: string;
  hint?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-2.5 flex items-end justify-between gap-4">
      <div className="flex items-baseline gap-2.5">
        {index !== undefined ? (
          <span className="font-mono text-2xs tabular text-ink-ghost">
            {String(index).padStart(2, '0')}
          </span>
        ) : null}
        <h2 className="eyebrow text-ink-dim">{title}</h2>
        {hint ? <span className="text-2xs text-ink-ghost">{hint}</span> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
