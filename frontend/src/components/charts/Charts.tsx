import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SeverityDatum } from '@/types';
import type { DwellDatum, HourBucket, OccupancyPoint } from '@/utils/stats';
import { formatDuration, humanise } from '@/utils/format';
import { EmptyState } from '@/components/ui';
import { AXIS, CHART, ChartLegend, ChartTooltip } from './ChartPrimitives';

/**
 * Alerts by hour.
 *
 * Stacked bars rather than a line: the question is "when did incidents
 * cluster, and how bad were they?", which needs both volume and
 * composition in the same mark.
 */
export function AlertsByHourChart({ data, height = 200 }: { data: HourBucket[]; height?: number }) {
  if (!data.some((point) => point.total > 0)) {
    return <EmptyState title="No alerts in window" description="Nothing raised in the last 24 hours." positive />;
  }

  return (
    <div style={{ height }} className="w-full pb-1 pr-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 4, left: -22, bottom: 0 }} barCategoryGap="18%">
          <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" {...AXIS} interval="preserveStartEnd" minTickGap={26} />
          <YAxis {...AXIS} allowDecimals={false} width={34} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey="other" name="Other" stackId="a" fill={CHART.info} fillOpacity={0.55} />
          <Bar dataKey="high" name="High" stackId="a" fill={CHART.warn} fillOpacity={0.85} />
          <Bar dataKey="critical" name="Critical" stackId="a" fill={CHART.crit} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Alerts by severity.
 *
 * A donut with the total in the middle: the running count is the figure
 * read first, and the ring explains how it breaks down.
 */
export function SeverityChart({ data, height = 190 }: { data: SeverityDatum[]; height?: number }) {
  const total = data.reduce((sum, datum) => sum + datum.value, 0);

  if (total === 0) {
    return <EmptyState title="No alerts to break down" positive />;
  }

  return (
    <div className="flex items-center gap-3">
      <div style={{ height, width: height }} className="relative shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={<ChartTooltip />} />
            <Pie
              data={data}
              dataKey="value"
              nameKey="label"
              innerRadius="64%"
              outerRadius="92%"
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
            <p className="font-mono text-2xl font-semibold tabular leading-none text-ink">
              {total}
            </p>
            <p className="mt-0.5 text-2xs uppercase tracking-wider text-ink-ghost">Alerts</p>
          </div>
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <ChartLegend
          items={data.map((datum) => ({
            label: datum.label,
            value: datum.value,
            color: datum.color,
            share: datum.value / total,
          }))}
        />
      </div>
    </div>
  );
}

/**
 * Zone-wise violations.
 *
 * Horizontal bars because zone names are long — rotated labels under a
 * vertical chart are far harder to scan.
 */
export function ZoneViolationsChart({
  data,
  height = 200,
}: {
  data: Array<{ zone: string; total: number; critical: number; color: string }>;
  height?: number;
}) {
  if (data.length === 0) {
    return <EmptyState title="No zone activity" description="No violations recorded against a zone." positive />;
  }

  return (
    <div style={{ height }} className="w-full pb-1 pr-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" horizontal={false} />
          <XAxis type="number" {...AXIS} allowDecimals={false} />
          <YAxis type="category" dataKey="zone" {...AXIS} width={92} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey="total" name="Violations" radius={[0, 2, 2, 0]} barSize={14}>
            {data.map((row) => (
              <Cell key={row.zone} fill={row.color} fillOpacity={0.8} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Occupancy trend.
 *
 * Total occupancy as a filled area with people overlaid as a line: the
 * gap between them is forklifts and equipment, which is exactly the
 * comparison a floor supervisor cares about.
 */
export function OccupancyChart({
  data,
  height = 200,
}: {
  data: OccupancyPoint[];
  height?: number;
}) {
  if (!data.some((point) => point.occupancy > 0)) {
    return <EmptyState title="No occupancy recorded" description="No tracked objects in this window." />;
  }

  return (
    <div style={{ height }} className="w-full pb-1 pr-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 4, left: -22, bottom: 0 }}>
          <defs>
            <linearGradient id="occFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART.info} stopOpacity={0.35} />
              <stop offset="100%" stopColor={CHART.info} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" {...AXIS} interval="preserveStartEnd" minTickGap={26} />
          <YAxis {...AXIS} allowDecimals={false} width={34} />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: CHART.grid }} />
          <Area
            type="monotone"
            dataKey="occupancy"
            name="All objects"
            stroke={CHART.info}
            strokeWidth={1.5}
            fill="url(#occFill)"
          />
          <Line
            type="monotone"
            dataKey="people"
            name="Workers"
            stroke={CHART.safe}
            strokeWidth={2}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Average dwell time per class.
 *
 * Mean and peak are shown together because a high mean and a high peak
 * mean different things: sustained presence versus one long outlier.
 */
export function DwellChart({ data, height = 200 }: { data: DwellDatum[]; height?: number }) {
  if (data.length === 0) {
    return <EmptyState title="No dwell data" description="Dwell needs tracks with a first and last sighting." />;
  }

  const rows = data.map((datum) => ({
    ...datum,
    label: humanise(datum.className),
    avgMinutes: Number((datum.average / 60).toFixed(2)),
    peakMinutes: Number((datum.peak / 60).toFixed(2)),
  }));

  return (
    <div style={{ height }} className="w-full pb-1 pr-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" horizontal={false} />
          <XAxis
            type="number"
            {...AXIS}
            tickFormatter={(value: number) => formatDuration(value * 60)}
          />
          <YAxis type="category" dataKey="label" {...AXIS} width={78} />
          <Tooltip
            content={<ChartTooltip unit=" min" />}
            cursor={{ fill: 'rgba(255,255,255,0.03)' }}
          />
          <Bar dataKey="peakMinutes" name="Peak" fill={CHART.neutral} fillOpacity={0.35} radius={[0, 2, 2, 0]} barSize={13} />
          <Bar dataKey="avgMinutes" name="Average" fill={CHART.info} radius={[0, 2, 2, 0]} barSize={13} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Top rules by alert volume. */
export function RuleBreakdownChart({
  data,
  height = 200,
}: {
  data: Array<{ name: string; value: number }>;
  height?: number;
}) {
  if (data.length === 0) return <EmptyState title="No rule activity" positive />;

  const rows = data.map((row) => ({ ...row, label: humanise(row.name.replace(/Rule$/, '')) }));

  return (
    <div style={{ height }} className="w-full pb-1 pr-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" horizontal={false} />
          <XAxis type="number" {...AXIS} allowDecimals={false} />
          <YAxis type="category" dataKey="label" {...AXIS} width={96} />
          <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey="value" name="Alerts" radius={[0, 2, 2, 0]} barSize={14}>
            {rows.map((row, index) => (
              <Cell
                key={row.name}
                fill={index === 0 ? CHART.crit : CHART.info}
                fillOpacity={index === 0 ? 0.85 : 0.6}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
