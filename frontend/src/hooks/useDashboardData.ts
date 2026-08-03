import { useMemo } from 'react';
import type { Alert, SeverityDatum, SystemEvent } from '@/types';
import {
  alertTrend,
  categoryDistribution,
  ruleDistribution,
  severityDistribution,
  summariseAlerts,
  type AlertSummary,
  type TrendPoint,
} from '@/utils/stats';
import { useAlerts } from './useAlerts';
import { useSystemEvents } from './useSystemEvents';

interface DashboardData {
  summary: AlertSummary;
  severity: SeverityDatum[];
  categories: Array<{ name: string; value: number }>;
  rules: Array<{ name: string; value: number }>;
  trend: TrendPoint[];
  recentAlerts: Alert[];
  openAlerts: Alert[];
  recentEvents: SystemEvent[];
  totalAlerts: number;
  isLoading: boolean;
  isFetching: boolean;
  error: Error | null;
  refetch: () => void;
}

/** Page size used for the analytical sample backing the charts. */
const ANALYSIS_SAMPLE_SIZE = 200;

/**
 * Assemble everything the dashboard overview needs.
 *
 * The backend exposes no aggregate endpoint, so the figures are derived
 * client-side from a recent sample. The sample is capped, which means
 * the charts describe *recent activity* rather than all history — the
 * headline totals come from the API's `meta.total`, which is exact.
 */
export function useDashboardData(refreshMs = 20_000): DashboardData {
  const alertsQuery = useAlerts(
    { page: 1, page_size: ANALYSIS_SAMPLE_SIZE, sort_by: 'occurred_at', order: 'desc' },
    refreshMs,
  );

  const openQuery = useAlerts(
    { page: 1, page_size: 8, status: 'active', sort_by: 'occurred_at', order: 'desc' },
    refreshMs,
  );

  const eventsQuery = useSystemEvents(
    { page: 1, page_size: 6, sort_by: 'occurred_at', order: 'desc' },
    refreshMs,
  );

  const alerts = useMemo(() => alertsQuery.data?.items ?? [], [alertsQuery.data]);

  return useMemo(
    () => ({
      summary: summariseAlerts(alerts),
      severity: severityDistribution(alerts),
      categories: categoryDistribution(alerts),
      rules: ruleDistribution(alerts),
      trend: alertTrend(alerts),
      recentAlerts: alerts.slice(0, 8),
      openAlerts: openQuery.data?.items ?? [],
      recentEvents: eventsQuery.data?.items ?? [],
      totalAlerts: alertsQuery.data?.meta.total ?? 0,
      isLoading: alertsQuery.isLoading,
      isFetching: alertsQuery.isFetching || openQuery.isFetching || eventsQuery.isFetching,
      error: (alertsQuery.error as Error | null) ?? null,
      refetch: () => {
        void alertsQuery.refetch();
        void openQuery.refetch();
        void eventsQuery.refetch();
      },
    }),
    [alerts, alertsQuery, openQuery, eventsQuery],
  );
}
