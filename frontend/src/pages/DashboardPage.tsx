import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Eye,
  PieChart,
  Siren,
  TrendingUp,
} from 'lucide-react';
import { useDashboardData, useHealth } from '@/hooks';
import { AppLayout } from '@/components/layout';
import {
  ChartSkeleton,
  ErrorState,
  Panel,
  PanelBody,
  PanelHeader,
  StatCard,
  StatSkeleton,
} from '@/components/ui';
import { AlertTrendChart, RuleBreakdownChart, SeverityChart, SeverityLegend } from '@/components/charts';
import { AlertFeed, AlertFeedFooter } from '@/components/alerts';
import { ActivityFeed, CameraPanel, SystemStatusPanel } from '@/components/dashboard';

/**
 * Operations overview.
 *
 * Composition only: every figure comes from `useDashboardData`, so this
 * page contains no aggregation, no fetching and no formatting logic.
 */
export function DashboardPage() {
  const navigate = useNavigate();
  const data = useDashboardData();
  const health = useHealth();

  const openCount = data.summary.active + data.summary.acknowledged;

  return (
    <AppLayout
      title="Operations Overview"
      subtitle="Live warehouse safety monitoring"
      onRefresh={data.refetch}
      isRefreshing={data.isFetching}
    >
      {data.error ? (
        <ErrorState error={data.error} onRetry={data.refetch} className="rounded-xl border border-surface-700/70 bg-surface-850/80" />
      ) : (
        <div className="space-y-5">
          {/* KPI row */}
          <section
            aria-label="Key metrics"
            className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            {data.isLoading ? (
              Array.from({ length: 4 }).map((_, index) => <StatSkeleton key={index} />)
            ) : (
              <>
                <StatCard
                  label="Active Alerts"
                  value={data.summary.active}
                  icon={<Siren className="h-4 w-4" />}
                  tone={data.summary.active > 0 ? 'danger' : 'success'}
                  emphasise={data.summary.active > 0}
                  hint={
                    data.summary.active > 0
                      ? 'Awaiting operator acknowledgement'
                      : 'No incidents need attention'
                  }
                />
                <StatCard
                  label="Critical Severity"
                  value={data.summary.critical}
                  icon={<AlertTriangle className="h-4 w-4" />}
                  tone={data.summary.critical > 0 ? 'warning' : 'neutral'}
                  emphasise={data.summary.critical > 0}
                  hint={`${data.summary.escalated} escalated after being raised`}
                />
                <StatCard
                  label="Total Observations"
                  value={data.summary.observations}
                  icon={<Eye className="h-4 w-4" />}
                  tone="accent"
                  hint="Frames folded into these incidents"
                />
                <StatCard
                  label="Resolved"
                  value={data.summary.resolved}
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  tone="success"
                  hint={`${openCount} still open`}
                />
              </>
            )}
          </section>

          {/* Live pipeline + system status */}
          <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <CameraPanel events={data.recentEvents} isLoading={data.isLoading} />
            </div>
            <SystemStatusPanel
              health={health.data}
              isLoading={health.isLoading}
              isError={health.isError}
            />
          </section>

          {/* Trend + severity mix */}
          <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
            <Panel className="xl:col-span-2">
              <PanelHeader
                title="Alert Volume"
                description="Last 24 hours, bucketed"
                icon={<TrendingUp className="h-4 w-4" />}
              />
              {data.isLoading ? <ChartSkeleton /> : <AlertTrendChart data={data.trend} />}
            </Panel>

            <Panel>
              <PanelHeader
                title="Severity Mix"
                description="Recent alert sample"
                icon={<PieChart className="h-4 w-4" />}
              />
              {data.isLoading ? (
                <ChartSkeleton />
              ) : (
                <>
                  <SeverityChart data={data.severity} height={200} />
                  <PanelBody className="pt-0">
                    <SeverityLegend data={data.severity} />
                  </PanelBody>
                </>
              )}
            </Panel>
          </section>

          {/* Active alerts + rule breakdown */}
          <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
            <Panel className="flex flex-col xl:col-span-2">
              <PanelHeader
                title="Active Alerts"
                description="Incidents awaiting acknowledgement"
                icon={<Siren className="h-4 w-4" />}
              />
              <div className="flex-1">
                <AlertFeed
                  alerts={data.openAlerts}
                  isLoading={data.isLoading}
                  emptyTitle="Nothing needs attention"
                  emptyDescription="No active alerts on the floor right now."
                  onSelect={(alert) => navigate(`/alerts?focus=${alert.alert_id}`)}
                />
              </div>
              <AlertFeedFooter to="/alerts?status=active" label="View all alerts" />
            </Panel>

            <Panel>
              <PanelHeader
                title="Top Rules"
                description="Most frequently triggered"
                icon={<BarChart3 className="h-4 w-4" />}
              />
              {data.isLoading ? <ChartSkeleton /> : <RuleBreakdownChart data={data.rules} />}
            </Panel>
          </section>

          {/* Recent activity */}
          <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
            <Panel className="flex flex-col xl:col-span-2">
              <PanelHeader
                title="Latest Alerts"
                description="Most recent incidents across all statuses"
                icon={<AlertTriangle className="h-4 w-4" />}
              />
              <div className="flex-1">
                <AlertFeed
                  alerts={data.recentAlerts}
                  isLoading={data.isLoading}
                  showStatus
                  emptyTitle="No alerts recorded"
                  emptyDescription="Alerts raised by the pipeline will appear here."
                  onSelect={(alert) => navigate(`/alerts?focus=${alert.alert_id}`)}
                />
              </div>
              <AlertFeedFooter to="/alerts" label="Open alerts table" />
            </Panel>

            <ActivityFeed events={data.recentEvents} isLoading={data.isLoading} />
          </section>
        </div>
      )}
    </AppLayout>
  );
}
