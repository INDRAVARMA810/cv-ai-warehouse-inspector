import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertOctagon,
  BarChart3,
  CalendarClock,
  Clock,
  Cpu,
  Gauge,
  HardHat,
  LayoutList,
  MapPin,
  PieChart,
  Siren,
  Users,
} from 'lucide-react';
import { ANALYSIS_SAMPLE_SIZE, useDashboardData } from '@/hooks';
import type { Alert, Column } from '@/types';
import { AppLayout } from '@/components/layout';
import {
  ChartSkeleton,
  DataTable,
  ErrorState,
  LevelBadge,
  Panel,
  PanelBody,
  PanelHeader,
  SectionHeading,
  StatCard,
  StatusBadge,
} from '@/components/ui';
import {
  AlertsByHourChart,
  DwellChart,
  OccupancyChart,
  RuleBreakdownChart,
  SeverityChart,
  ZoneViolationsChart,
} from '@/components/charts';
import { ActivityFeed, CameraPanel, SystemStatusPanel } from '@/components/dashboard';
import { formatDateTime, formatRelative, humanise, truncate } from '@/utils/format';
import { levelTone } from '@/utils/severity';

/**
 * Operations overview.
 *
 * Composition only — every figure comes from `useDashboardData`, so this
 * page contains no aggregation, no fetching and no formatting logic.
 *
 * Sections are numbered so they can be referred to over a radio: "check
 * section 3" is unambiguous in a control room.
 */
export function DashboardPage() {
  const navigate = useNavigate();
  const data = useDashboardData();

  const columns = useMemo<Column<Alert>[]>(
    () => [
      {
        key: 'level',
        header: 'Severity',
        render: (row) => <LevelBadge level={row.level} live={row.status === 'active'} />,
      },
      {
        key: 'track_id',
        header: 'Track',
        render: (row) => (
          <span className="font-mono tabular text-ink">
            {row.track_id !== null ? `#${row.track_id}` : '—'}
          </span>
        ),
      },
      {
        key: 'rule_name',
        header: 'Rule',
        hideOnMobile: true,
        render: (row) => (
          <span className="whitespace-nowrap">{humanise(row.rule_name.replace(/Rule$/, ''))}</span>
        ),
      },
      {
        key: 'zone',
        header: 'Zone',
        hideOnMobile: true,
        render: (row) => {
          const zone = row.metadata?.zone_name as string | undefined;
          return zone ? (
            <span className="inline-flex items-center gap-1 font-mono text-2xs text-ink-dim">
              <MapPin className="h-3 w-3 text-ink-ghost" />
              {zone}
            </span>
          ) : (
            <span className="text-ink-ghost">—</span>
          );
        },
      },
      {
        key: 'message',
        header: 'Detail',
        className: 'w-full',
        render: (row) => <span className="text-ink">{truncate(row.message, 62)}</span>,
      },
      {
        key: 'occurred_at',
        header: 'Timestamp',
        render: (row) => (
          <span
            className="whitespace-nowrap font-mono tabular text-ink-dim"
            title={formatDateTime(row.occurred_at)}
          >
            {formatRelative(row.occurred_at)}
          </span>
        ),
      },
      {
        key: 'status',
        header: 'Status',
        render: (row) => <StatusBadge status={row.status} />,
      },
    ],
    [],
  );

  if (data.error) {
    return (
      <AppLayout title="Operations Overview" onRefresh={data.refetch}>
        <Panel>
          <ErrorState error={data.error} onRetry={data.refetch} />
        </Panel>
      </AppLayout>
    );
  }

  const openAlerts = data.summary.active + data.summary.acknowledged;

  return (
    <AppLayout
      title="Operations Overview"
      subtitle="Live warehouse safety monitoring"
      onRefresh={data.refetch}
      isRefreshing={data.isFetching}
    >
      <div className="space-y-5">
        {/* ── 01 · Live feed + subsystem board ─────────────────────── */}
        <section>
          <SectionHeading index={1} title="Live Monitoring" hint="Annotated detection stream" />
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
            <CameraPanel className="xl:col-span-2" />
            <SystemStatusPanel />
          </div>
        </section>

        {/* ── 02 · KPI cluster ─────────────────────────────────────── */}
        <section>
          <SectionHeading index={2} title="Key Metrics" hint="Recent sample" />
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 2xl:grid-cols-6">
            <StatCard
              label="Workers"
              value={data.workers}
              icon={<Users className="h-3.5 w-3.5" />}
              tone={data.workers > 0 ? 'info' : 'neutral'}
              hint="Tracked in last 15 min"
              isLoading={data.isLoading}
            />
            <StatCard
              label="Active Alerts"
              value={data.summary.active}
              icon={<Siren className="h-3.5 w-3.5" />}
              tone={data.summary.active > 0 ? 'crit' : 'safe'}
              hint={openAlerts > 0 ? `${openAlerts} open total` : 'Nothing outstanding'}
              series={data.alertSeries}
              delta={data.alertDelta}
              isLoading={data.isLoading}
            />
            <StatCard
              label="Critical Alerts"
              value={data.summary.critical}
              icon={<AlertOctagon className="h-3.5 w-3.5" />}
              tone={data.summary.critical > 0 ? 'crit' : 'safe'}
              hint={`${data.summary.escalated} escalated after raise`}
              isLoading={data.isLoading}
            />
            <StatCard
              label="Violations Today"
              value={data.summary.today}
              icon={<CalendarClock className="h-3.5 w-3.5" />}
              tone={data.summary.today > 0 ? 'warn' : 'safe'}
              hint={`${data.totalViolations} recorded all time`}
              isLoading={data.isLoading}
            />
            <StatCard
              label="Average FPS"
              value={data.fps !== null ? data.fps.toFixed(1) : '––'}
              unit="fps"
              icon={<Gauge className="h-3.5 w-3.5" />}
              tone={data.fps === null ? 'neutral' : data.fps >= 10 ? 'safe' : 'warn'}
              hint={data.fps === null ? 'Stream idle' : 'Pipeline throughput'}
              isLoading={data.isLoading}
            />
            <StatCard
              label="GPU Load"
              value={
                data.gpuUtilisation !== null ? Math.round(data.gpuUtilisation * 100) : '––'
              }
              unit="%"
              icon={<Cpu className="h-3.5 w-3.5" />}
              tone={data.device === 'cuda' ? 'safe' : data.device ? 'info' : 'neutral'}
              hint={data.device ? `${data.device.toUpperCase()} · fps vs 30 target` : 'No device'}
              fill={data.gpuUtilisation}
              isLoading={data.isLoading}
            />
          </div>
        </section>

        {/* ── 03 · Analytics ───────────────────────────────────────── */}
        <section>
          <SectionHeading index={3} title="Analytics" hint="Derived from recent records" />
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
            <Panel className="xl:col-span-2">
              <PanelHeader
                title="Alerts by Hour"
                subtitle="Trailing 24 hours, stacked by severity"
                icon={<BarChart3 className="h-3.5 w-3.5" />}
              />
              {data.isLoading ? <ChartSkeleton /> : <AlertsByHourChart data={data.hourly} />}
            </Panel>

            <Panel>
              <PanelHeader
                title="Alerts by Severity"
                subtitle="Distribution"
                icon={<PieChart className="h-3.5 w-3.5" />}
              />
              <PanelBody className="p-3">
                {data.isLoading ? <ChartSkeleton height={190} /> : <SeverityChart data={data.severity} />}
              </PanelBody>
            </Panel>

            <Panel>
              <PanelHeader
                title="Zone-wise Violations"
                subtitle="By configured zone"
                icon={<MapPin className="h-3.5 w-3.5" />}
              />
              {data.isLoading ? <ChartSkeleton /> : <ZoneViolationsChart data={data.zones} />}
            </Panel>

            <Panel>
              <PanelHeader
                title="Occupancy Trend"
                subtitle="Objects on floor, trailing 8 hours"
                icon={<Users className="h-3.5 w-3.5" />}
              />
              {data.isLoading ? <ChartSkeleton /> : <OccupancyChart data={data.occupancy} />}
            </Panel>

            <Panel>
              <PanelHeader
                title="Average Dwell Time"
                subtitle="Mean and peak, by object class"
                icon={<Clock className="h-3.5 w-3.5" />}
              />
              {data.isLoading ? <ChartSkeleton /> : <DwellChart data={data.dwell} />}
            </Panel>
          </div>
        </section>

        {/* ── 04 · Recent alerts ───────────────────────────────────── */}
        <section>
          <SectionHeading
            index={4}
            title="Recent Alerts"
            hint={`${data.totalAlerts} total`}
          />
          <Panel className="overflow-hidden">
            <PanelHeader
              title="Alert Register"
              subtitle="Most recent incidents across all statuses"
              icon={<LayoutList className="h-3.5 w-3.5" />}
              rail={data.summary.active > 0 ? 'shadow-rail-crit' : undefined}
            />
            <DataTable
              columns={columns}
              rows={data.recentAlerts}
              rowKey={(row) => row.alert_id}
              isLoading={data.isLoading}
              isFetching={data.isFetching}
              rowRail={(row) => levelTone(row.level).rail}
              onRowClick={(row) => navigate(`/alerts?focus=${row.alert_id}`)}
              emptyTitle="No alerts recorded"
              emptyDescription="Incidents raised by the pipeline will appear here."
              emptyPositive
            />
          </Panel>
        </section>

        {/* ── 05 · Rules + activity ────────────────────────────────── */}
        <section>
          <SectionHeading index={5} title="Diagnostics" hint="Rule activity and system log" />
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
            <Panel className="xl:col-span-2">
              <PanelHeader
                title="Top Rules"
                subtitle="Most frequently triggered"
                icon={<Activity className="h-3.5 w-3.5" />}
              />
              {data.isLoading ? <ChartSkeleton /> : <RuleBreakdownChart data={data.rules} />}
            </Panel>

            <ActivityFeed events={data.recentEvents} isLoading={data.isLoading} />
          </div>
        </section>

        <p className="flex items-center gap-1.5 px-0.5 pb-2 text-2xs text-ink-ghost">
          <HardHat className="h-3 w-3" />
          Charts derive from the most recent {ANALYSIS_SAMPLE_SIZE} records. Totals shown on tiles are exact
          counts reported by the API.
        </p>
      </div>
    </AppLayout>
  );
}
