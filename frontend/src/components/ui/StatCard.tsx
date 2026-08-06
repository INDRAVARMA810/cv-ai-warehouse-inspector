import type { ReactNode } from 'react';
import { AlertTriangle, Minus, TrendingDown, TrendingUp } from 'lucide-react';
import { cn } from '@/utils/cn';
import { formatNumber } from '@/utils/format';
import { Skeleton } from './Skeleton';

type Tone = 'neutral' | 'safe' | 'warn' | 'crit' | 'info';

const TONES: Record<Tone, { value: string; rail: string; icon: string; spark: string }> = {
  neutral: { value: 'text-ink', rail: '', icon: 'text-ink-faint', spark: '#5E6873' },
  safe: { value: 'text-safe', rail: 'shadow-rail-safe', icon: 'text-safe', spark: '#10B981' },
  warn: { value: 'text-warn', rail: 'shadow-rail-warn', icon: 'text-warn', spark: '#F59E0B' },
  crit: { value: 'text-crit', rail: 'shadow-rail-crit', icon: 'text-crit', spark: '#EF4444' },
  info: { value: 'text-info', rail: 'shadow-rail-info', icon: 'text-info', spark: '#3B82F6' },
};

interface StatCardProps {
  label: string;
  value: number | string;
  /** Appended to the value at reduced weight, e.g. "fps" or "%". */
  unit?: string;
  icon?: ReactNode;
  hint?: string;
  tone?: Tone;
  /** Percentage change vs. the previous period. */
  delta?: number | null;
  /** Whether a rising value is good; flips the delta's colour. */
  higherIsBetter?: boolean;
  /** Values for a background sparkline, oldest first. */
  series?: number[];
  /** 0–1 fill for a bottom progress bar, e.g. GPU utilisation. */
  fill?: number | null;
  isLoading?: boolean;
  isError?: boolean;
  className?: string;
}

/**
 * Headline metric tile.
 *
 * The number is the only thing that should be legible from across a
 * room, so it is set large in tabular mono while the label stays small
 * and quiet. A left status rail carries the tone, which keeps the tile
 * itself neutral until something is actually wrong.
 */
export function StatCard({
  label,
  value,
  unit,
  icon,
  hint,
  tone = 'neutral',
  delta = null,
  higherIsBetter = false,
  series,
  fill = null,
  isLoading = false,
  isError = false,
  className,
}: StatCardProps) {
  const palette = TONES[tone];

  if (isLoading) {
    return (
      <article
        className={cn(
          'rounded-panel border border-edge bg-panel p-3.5 shadow-panel',
          className,
        )}
      >
        <Skeleton className="h-2.5 w-20" />
        <Skeleton className="mt-3.5 h-8 w-24" />
        <Skeleton className="mt-3 h-2.5 w-28" />
      </article>
    );
  }

  if (isError) {
    return (
      <article
        className={cn(
          'rounded-panel border border-crit/30 bg-panel p-3.5 shadow-panel shadow-rail-crit',
          className,
        )}
      >
        <p className="eyebrow">{label}</p>
        <div className="mt-3 flex items-center gap-2 text-crit">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span className="font-mono text-xl tabular">––</span>
        </div>
        <p className="mt-2 text-2xs text-ink-faint">Metric unavailable</p>
      </article>
    );
  }

  return (
    <article
      className={cn(
        'group relative overflow-hidden rounded-panel border border-edge bg-panel p-3.5 shadow-panel',
        'transition-colors duration-200 ease-instrument hover:border-edge-strong hover:bg-panel-raised',
        palette.rail,
        className,
      )}
    >
      {series && series.length > 1 ? (
        <Sparkline values={series} color={palette.spark} />
      ) : null}

      <div className="relative flex items-start justify-between gap-2">
        <p className="eyebrow truncate">{label}</p>
        {icon ? <span className={cn('shrink-0', palette.icon)}>{icon}</span> : null}
      </div>

      <div className="relative mt-2.5 flex items-baseline gap-1.5">
        <span
          className={cn('font-mono text-kpi font-semibold tabular', palette.value)}
        >
          {typeof value === 'number' ? formatNumber(value) : value}
        </span>
        {unit ? (
          <span className="font-mono text-xs text-ink-faint">{unit}</span>
        ) : null}
        {delta !== null && delta !== undefined ? (
          <DeltaChip value={delta} higherIsBetter={higherIsBetter} />
        ) : null}
      </div>

      {hint ? (
        <p className="relative mt-1.5 truncate text-2xs text-ink-faint">{hint}</p>
      ) : null}

      {fill !== null && fill !== undefined ? (
        <div className="relative mt-3 h-1 overflow-hidden rounded-full bg-edge-soft">
          <div
            className="h-full rounded-full transition-[width] duration-500 ease-instrument"
            style={{
              width: `${Math.max(0, Math.min(1, fill)) * 100}%`,
              backgroundColor: palette.spark,
            }}
          />
        </div>
      ) : null}
    </article>
  );
}

/** Period-over-period change chip. */
function DeltaChip({
  value,
  higherIsBetter,
}: {
  value: number;
  higherIsBetter: boolean;
}) {
  const flat = Math.abs(value) < 0.5;
  const rising = value > 0;
  const good = flat ? null : rising === higherIsBetter;

  const Icon = flat ? Minus : rising ? TrendingUp : TrendingDown;

  return (
    <span
      className={cn(
        'ml-1 inline-flex items-center gap-0.5 font-mono text-2xs tabular',
        good === null ? 'text-ink-faint' : good ? 'text-safe' : 'text-crit',
      )}
      title="Change vs. previous period"
    >
      <Icon className="h-3 w-3" />
      {flat ? '0%' : `${Math.abs(Math.round(value))}%`}
    </span>
  );
}

/**
 * Background sparkline.
 *
 * Deliberately low contrast and behind the number: it provides shape
 * and direction without competing with the figure it describes.
 */
function Sparkline({ values, color }: { values: number[]; color: string }) {
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;

  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 100;
      const y = 100 - ((value - min) / span) * 100;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');

  return (
    <svg
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden
      className="pointer-events-none absolute inset-x-0 bottom-0 h-12 w-full opacity-[0.16] transition-opacity duration-300 group-hover:opacity-30"
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2.5"
        vectorEffect="non-scaling-stroke"
        strokeLinejoin="round"
      />
      <polygon points={`0,100 ${points} 100,100`} fill={color} opacity="0.25" />
    </svg>
  );
}
