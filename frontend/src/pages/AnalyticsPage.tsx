import { BarChart3, Clock, Layers, MapPin, PieChart, TrendingUp, Users } from 'lucide-react';
import { useDashboardData } from '@/hooks';
import { AppLayout } from '@/components/layout';
import {
  ChartSkeleton,
  ErrorState,
  Panel,
  PanelBody,
  PanelHeader,
  SectionHeading,
  StatCard,
} from '@/components/ui';
import {
  AlertsByHourChart,
  DwellChart,
  OccupancyChart,
  RuleBreakdownChart,
  SeverityChart,
  ZoneViolationsChart,
} from '@/components/charts';
import { formatDuration } from '@/utils/format';

/**
 * Analytical view.
 *
 * The same derivations as the dashboard, given room to breathe. Where
 * the dashboard answers "what is happening now", this answers "what has
 * been happening" — so charts are larger and paired with the summary
 * figures that put them in context.
 */
export function AnalyticsPage() {
  const data = useDashboardData(60_000);

  const peakHour = data.hourly.reduce(
    (best, bucket) => (bucket.total > best.total ? bucket : best),
    data.hourly[0] ?? { label: '––', total: 0 },
  );

  const busiestZone = data.zones[0];
  const longestDwell = data.dwell[0];

  if (data.error) {
    return (
      <AppLayout title="Analytics" onRefresh={data.refetch}>
        <Panel>
          <ErrorState error={data.error} onRetry={data.refetch} />
        </Panel>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      title="Analytics"
      subtitle="Trends across recent activity"
      onRefresh={data.refetch}
      isRefreshing={data.isFetching}
    >
      <div className="space-y-5">
        <section>
          <SectionHeading title="Highlights" hint="Derived from the recent sample" />
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Peak Hour"
              value={peakHour?.label ?? '––'}
              icon={<TrendingUp className="h-3.5 w-3.5" />}
              tone={peakHour?.total > 0 ? 'warn' : 'neutral'}
              hint={`${peakHour?.total ?? 0} alerts in that hour`}
              isLoading={data.isLoading}
            />
            <StatCard
              label="Busiest Zone"
              value={busiestZone?.zone ?? '––'}
              icon={<MapPin className="h-3.5 w-3.5" />}
              tone={busiestZone?.critical ? 'crit' : busiestZone ? 'warn' : 'neutral'}
              hint={
                busiestZone
                  ? `${busiestZone.total} violations · ${busiestZone.critical} critical`
                  : 'No zone data'
              }
              isLoading={data.isLoading}
            />
            <StatCard
              label="Longest Dwell"
              value={longestDwell ? formatDuration(longestDwell.average) : '––'}
              icon={<Clock className="h-3.5 w-3.5" />}
              tone="info"
              hint={
                longestDwell
                  ? `${longestDwell.className} · ${longestDwell.samples} tracks`
                  : 'No dwell data'
              }
              isLoading={data.isLoading}
            />
            <StatCard
              label="Total Observations"
              value={data.summary.observations}
              icon={<Layers className="h-3.5 w-3.5" />}
              tone="info"
              hint={`Across ${data.summary.total} incidents`}
              series={data.alertSeries}
              isLoading={data.isLoading}
            />
          </div>
        </section>

        <section>
          <SectionHeading title="Alert Volume" />
          <Panel>
            <PanelHeader
              title="Alerts by Hour"
              subtitle="Trailing 24 hours, stacked by severity"
              icon={<BarChart3 className="h-3.5 w-3.5" />}
            />
            {data.isLoading ? (
              <ChartSkeleton height={300} />
            ) : (
              <AlertsByHourChart data={data.hourly} height={300} />
            )}
          </Panel>
        </section>

        <section>
          <SectionHeading title="Distribution" />
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <Panel>
              <PanelHeader
                title="Alerts by Severity"
                icon={<PieChart className="h-3.5 w-3.5" />}
              />
              <PanelBody>
                {data.isLoading ? (
                  <ChartSkeleton height={230} />
                ) : (
                  <SeverityChart data={data.severity} height={230} />
                )}
              </PanelBody>
            </Panel>

            <Panel>
              <PanelHeader
                title="Zone-wise Violations"
                icon={<MapPin className="h-3.5 w-3.5" />}
              />
              {data.isLoading ? (
                <ChartSkeleton height={250} />
              ) : (
                <ZoneViolationsChart data={data.zones} height={250} />
              )}
            </Panel>

            <Panel>
              <PanelHeader
                title="Occupancy Trend"
                subtitle="Objects on floor, trailing 8 hours"
                icon={<Users className="h-3.5 w-3.5" />}
              />
              {data.isLoading ? (
                <ChartSkeleton height={250} />
              ) : (
                <OccupancyChart data={data.occupancy} height={250} />
              )}
            </Panel>

            <Panel>
              <PanelHeader
                title="Average Dwell Time"
                subtitle="Mean and peak, by object class"
                icon={<Clock className="h-3.5 w-3.5" />}
              />
              {data.isLoading ? (
                <ChartSkeleton height={250} />
              ) : (
                <DwellChart data={data.dwell} height={250} />
              )}
            </Panel>
          </div>
        </section>

        <section>
          <SectionHeading title="Rule Activity" />
          <Panel>
            <PanelHeader
              title="Top Rules"
              subtitle="Most frequently triggered"
              icon={<Layers className="h-3.5 w-3.5" />}
            />
            {data.isLoading ? (
              <ChartSkeleton height={260} />
            ) : (
              <RuleBreakdownChart data={data.rules} height={260} />
            )}
          </Panel>
        </section>
      </div>
    </AppLayout>
  );
}
