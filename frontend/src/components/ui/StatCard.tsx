import type { ReactNode } from 'react';
import { cn } from '@/utils/cn';
import { formatNumber } from '@/utils/format';

type Tone = 'neutral' | 'accent' | 'warning' | 'danger' | 'success';

interface StatCardProps {
  label: string;
  value: number | string;
  icon?: ReactNode;
  /** Short qualifier beneath the value, e.g. "of 1,204 total". */
  hint?: string;
  tone?: Tone;
  /** Emphasises the tile when the figure needs attention. */
  emphasise?: boolean;
  className?: string;
}

const TONES: Record<Tone, { value: string; icon: string; ring: string }> = {
  neutral: {
    value: 'text-content-primary',
    icon: 'text-content-secondary border-surface-700 bg-surface-800',
    ring: '',
  },
  accent: {
    value: 'text-accent',
    icon: 'text-accent border-accent/30 bg-accent/10',
    ring: '',
  },
  warning: {
    value: 'text-amber-300',
    icon: 'text-amber-300 border-amber-500/30 bg-amber-500/10',
    ring: 'ring-1 ring-amber-500/20',
  },
  danger: {
    value: 'text-red-300',
    icon: 'text-red-300 border-red-500/30 bg-red-500/10',
    ring: 'ring-1 ring-red-500/25',
  },
  success: {
    value: 'text-emerald-300',
    icon: 'text-emerald-300 border-emerald-500/30 bg-emerald-500/10',
    ring: '',
  },
};

/**
 * Headline metric tile.
 *
 * The value is the largest element on the tile and uses tabular figures
 * so digits do not shift width as a live count updates.
 */
export function StatCard({
  label,
  value,
  icon,
  hint,
  tone = 'neutral',
  emphasise = false,
  className,
}: StatCardProps) {
  const palette = TONES[tone];

  return (
    <article
      className={cn(
        'rounded-xl border border-surface-700/70 bg-surface-850/80 p-5 shadow-panel',
        'transition-colors duration-200',
        emphasise && palette.ring,
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-medium uppercase tracking-wider text-content-muted">
          {label}
        </p>
        {icon ? (
          <span
            className={cn(
              'grid h-8 w-8 shrink-0 place-items-center rounded-lg border',
              palette.icon,
            )}
          >
            {icon}
          </span>
        ) : null}
      </div>

      <p
        className={cn(
          'mt-3 font-mono text-3xl font-semibold tabular-nums leading-none tracking-tight',
          palette.value,
        )}
      >
        {typeof value === 'number' ? formatNumber(value) : value}
      </p>

      {hint ? <p className="mt-2 text-xs text-content-muted">{hint}</p> : null}
    </article>
  );
}
