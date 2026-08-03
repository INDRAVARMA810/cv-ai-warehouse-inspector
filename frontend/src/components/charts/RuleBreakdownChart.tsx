import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { EmptyState } from '@/components/ui';
import { humanise } from '@/utils/format';
import { AXIS_PROPS, CHART_THEME, ChartTooltip } from './ChartPrimitives';

interface RuleBreakdownChartProps {
  data: Array<{ name: string; value: number }>;
  height?: number;
}

/**
 * Which rules fire most, as a horizontal bar chart.
 *
 * Horizontal because rule names are long: rotating labels under a
 * vertical chart would make them far harder to scan.
 */
export function RuleBreakdownChart({ data, height = 260 }: RuleBreakdownChartProps) {
  if (data.length === 0) {
    return <EmptyState title="No rule activity" className="py-12" />;
  }

  const rows = data.map((row) => ({ ...row, label: humanise(row.name.replace(/Rule$/, '')) }));

  return (
    <div style={{ height }} className="w-full px-2 pb-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid stroke={CHART_THEME.grid} strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" {...AXIS_PROPS} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="label"
            {...AXIS_PROPS}
            width={110}
            tick={{ fill: CHART_THEME.axis, fontSize: 11 }}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey="value" name="Alerts" radius={[0, 4, 4, 0]} barSize={16}>
            {rows.map((row, index) => (
              <Cell
                key={row.name}
                fill={index === 0 ? CHART_THEME.high : CHART_THEME.accent}
                fillOpacity={index === 0 ? 0.9 : 0.65}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
