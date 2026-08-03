import type { ReactNode } from 'react';

/**
 * Shared chart styling.
 *
 * Recharts is configured through props rather than CSS, so the tokens
 * that keep charts consistent with the rest of the interface live here
 * instead of being repeated in each chart.
 */
export const CHART_THEME = {
  grid: '#22303F',
  axis: '#64748B',
  tooltipBg: '#101722',
  tooltipBorder: '#2E3F52',
  accent: '#22D3EE',
  accentSoft: 'rgba(34,211,238,0.18)',
  critical: '#EF4444',
  high: '#FB7185',
} as const;

export const AXIS_PROPS = {
  stroke: CHART_THEME.axis,
  tick: { fill: CHART_THEME.axis, fontSize: 11 },
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
  /** Formats the label shown as the tooltip heading. */
  labelFormatter?: (label: string | number) => string;
}

/**
 * Tooltip matching the panel surface.
 *
 * Recharts' default tooltip is light-themed and would glare against the
 * dark interface, so it is replaced rather than restyled piecemeal.
 */
export function ChartTooltip({
  active,
  payload,
  label,
  labelFormatter,
}: ChartTooltipProps): ReactNode {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="rounded-lg border border-surface-600 bg-surface-850/95 px-3 py-2 shadow-panel backdrop-blur">
      {label !== undefined ? (
        <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-content-muted">
          {labelFormatter ? labelFormatter(label) : label}
        </p>
      ) : null}
      <ul className="space-y-1">
        {payload.map((row, index) => (
          <li key={index} className="flex items-center gap-2 text-xs">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: row.color ?? CHART_THEME.accent }}
            />
            <span className="text-content-secondary">{row.name}</span>
            <span className="ml-auto font-mono tabular-nums text-content-primary">
              {row.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
