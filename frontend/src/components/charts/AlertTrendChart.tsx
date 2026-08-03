import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TrendPoint } from '@/utils/stats';
import { EmptyState } from '@/components/ui';
import { AXIS_PROPS, CHART_THEME, ChartTooltip } from './ChartPrimitives';

interface AlertTrendChartProps {
  data: TrendPoint[];
  height?: number;
}

/**
 * Alert volume over the recent window, with severity stacked beneath.
 *
 * An area chart rather than bars: the question an operator asks of this
 * panel is "is it getting worse?", which is a question about shape over
 * time, not about comparing individual buckets.
 */
export function AlertTrendChart({ data, height = 260 }: AlertTrendChartProps) {
  const hasData = data.some((point) => point.total > 0);

  if (!hasData) {
    return (
      <EmptyState
        title="No alerts in this window"
        description="Nothing has been raised in the last 24 hours."
        className="py-12"
      />
    );
  }

  return (
    <div style={{ height }} className="w-full px-2 pb-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 12, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="trendTotal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.accent} stopOpacity={0.35} />
              <stop offset="100%" stopColor={CHART_THEME.accent} stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="trendCritical" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_THEME.critical} stopOpacity={0.4} />
              <stop offset="100%" stopColor={CHART_THEME.critical} stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid stroke={CHART_THEME.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="label" {...AXIS_PROPS} interval="preserveStartEnd" minTickGap={24} />
          <YAxis {...AXIS_PROPS} allowDecimals={false} width={40} />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: CHART_THEME.grid }} />

          <Area
            type="monotone"
            dataKey="total"
            name="All alerts"
            stroke={CHART_THEME.accent}
            strokeWidth={2}
            fill="url(#trendTotal)"
          />
          <Area
            type="monotone"
            dataKey="critical"
            name="Critical"
            stroke={CHART_THEME.critical}
            strokeWidth={2}
            fill="url(#trendCritical)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
