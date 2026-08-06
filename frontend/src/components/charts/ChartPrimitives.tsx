import type { ReactNode } from 'react';

/**
 * Shared chart theme.
 *
 * Recharts is configured through props rather than CSS, so the tokens
 * that keep charts consistent with the rest of the instrument live here
 * instead of being repeated per chart.
 */
export const CHART = {
  grid: '#1F2429',
  axis: '#5E6873',
  tooltipBg: '#131619',
  tooltipEdge: '#2A3138',
  safe: '#10B981',
  warn: '#F59E0B',
  crit: '#EF4444',
  info: '#3B82F6',
  neutral: '#5E6873',
} as const;

export const AXIS = {
  stroke: CHART.grid,
  tick: { fill: CHART.axis, fontSize: 10, fontFamily: 'JetBrains Mono Variable, monospace' },
  tickLine: false,
  axisLine: false,
} as const;

interface TooltipRow {
  name?: string | number;
  value?: string | number;
  color?: string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipRow[];
  label?: string | number;
  labelFormatter?: (label: string | number) => string;
  unit?: string;
}

/**
 * Tooltip matching the panel surface.
 *
 * Recharts ships a light-themed tooltip that would glare against the
 * dark instrument, so it is replaced rather than restyled piecemeal.
 */
export function ChartTooltip({
  active,
  payload,
  label,
  labelFormatter,
  unit,
}: ChartTooltipProps): ReactNode {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-control border border-edge-strong bg-panel-raised px-2.5 py-1.5 shadow-panel">
      {label !== undefined ? (
        <p className="mb-1 font-mono text-2xs uppercase tracking-wider text-ink-ghost">
          {labelFormatter ? labelFormatter(label) : label}
        </p>
      ) : null}
      <ul className="space-y-0.5">
        {payload.map((row, index) => (
          <li key={index} className="flex items-center gap-2 text-2xs">
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-[1px]"
              style={{ backgroundColor: row.color ?? CHART.info }}
            />
            <span className="text-ink-faint">{row.name}</span>
            <span className="ml-auto font-mono tabular font-medium text-ink">
              {row.value}
              {unit ? <span className="ml-0.5 text-ink-ghost">{unit}</span> : null}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Compact legend used beneath donut and stacked charts. */
export function ChartLegend({
  items,
}: {
  items: Array<{ label: string; value: number; color: string; share?: number }>;
}) {
  if (items.length === 0) return null;

  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-2 text-2xs">
          <span
            className="h-2 w-2 shrink-0 rounded-[1px]"
            style={{ backgroundColor: item.color }}
          />
          <span className="truncate text-ink-faint">{item.label}</span>
          <span className="ml-auto font-mono tabular text-ink">{item.value}</span>
          {item.share !== undefined ? (
            <span className="w-9 text-right font-mono tabular text-ink-ghost">
              {Math.round(item.share * 100)}%
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
