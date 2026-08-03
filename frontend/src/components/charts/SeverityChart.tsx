import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { SeverityDatum } from '@/types';
import { EmptyState } from '@/components/ui';
import { ChartTooltip } from './ChartPrimitives';

interface SeverityChartProps {
  data: SeverityDatum[];
  height?: number;
}

/**
 * Severity mix as a donut, with the total in the centre.
 *
 * A donut is used rather than a pie so the running total can sit in the
 * middle — the single figure an operator reads first — while the ring
 * still shows how that total breaks down.
 */
export function SeverityChart({ data, height = 260 }: SeverityChartProps) {
  const total = data.reduce((sum, datum) => sum + datum.value, 0);

  if (total === 0) {
    return <EmptyState title="No alerts to break down" className="py-12" />;
  }

  return (
    <div style={{ height }} className="relative w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip content={<ChartTooltip />} />
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            innerRadius="62%"
            outerRadius="88%"
            paddingAngle={2}
            stroke="none"
          >
            {data.map((datum) => (
              <Cell key={datum.level} fill={datum.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>

      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <div className="text-center">
          <p className="font-mono text-3xl font-semibold tabular-nums leading-none text-content-primary">
            {total}
          </p>
          <p className="mt-1 text-[11px] uppercase tracking-wider text-content-muted">Alerts</p>
        </div>
      </div>
    </div>
  );
}

/** Legend rendered beside the donut, showing counts and shares. */
export function SeverityLegend({ data }: { data: SeverityDatum[] }) {
  const total = data.reduce((sum, datum) => sum + datum.value, 0);
  if (total === 0) return null;

  return (
    <ul className="space-y-2">
      {data.map((datum) => (
        <li key={datum.level} className="flex items-center gap-2.5 text-xs">
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-sm"
            style={{ backgroundColor: datum.color }}
          />
          <span className="text-content-secondary">{datum.label}</span>
          <span className="ml-auto font-mono tabular-nums text-content-primary">
            {datum.value}
          </span>
          <span className="w-10 text-right font-mono tabular-nums text-content-muted">
            {Math.round((datum.value / total) * 100)}%
          </span>
        </li>
      ))}
    </ul>
  );
}
