import { useMemo } from 'react';
import type { Alert, SeverityDatum, SystemEvent, Track } from '@/types';
import {
  alertsByHour,
  categoryDistribution,
  dwellByClass,
  occupancyTrend,
  periodDelta,
  ruleDistribution,
  severityDistribution,
  summariseAlerts,
  workerCount,
  zoneViolations,
  type AlertSummary,
  type DwellDatum,
  type HourBucket,
  type OccupancyPoint,
} from '@/utils/stats';
import { useAlerts } from './useAlerts';
import { useStreamStatus } from './useMjpegStream';
import { useSystemEvents } from './useSystemEvents';
import { useTracks } from './useTracks';
import { useViolations } from './useViolations';

/** Sample size backing the derived charts. */
const SAMPLE = 200;

interface DashboardData {
  summary: AlertSummary;
  severity: SeverityDatum[];
  categories: Array<{ name: string; value: number }>;
  rules: Array<{ name: string; value: number }>;
  hourly: HourBucket[];
  occupancy: OccupancyPoint[];
  dwell: DwellDatum[];
  zones: Array<{ zone: string; total: number; critical: number; color: string }>;

  recentAlerts: Alert[];
  activeAlerts: Alert[];
  recentEvents: SystemEvent[];
  tracks: Track[];

  workers: number;
  totalAlerts: number;
  totalViolations: number;
  fps: number | null;
  gpuUtilisation: number | null;
  device: string | null;

  /** Sparkline series for the KPI tiles. */
  alertSeries: number[];
  alertDelta: number | null;

  isLoading: boolean;
  isFetching: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Assemble everything the dashboard overview needs.
 *
 * One hook so the KPI tiles, charts and tables are all computed from the
 * same fetch — otherwise two panels can disagree about the same number,
 * which erodes trust in the whole board.
 *
 * The backend exposes no aggregate endpoints, so these are *sample*
 * statistics over a recent page. Headline totals use the API's exact
 * `meta.total` rather than the sample length.
 */
export function useDashboardData(refreshMs = 20_000): DashboardData {
  const alertsQuery = useAlerts(
    { page: 1, page_size: SAMPLE, sort_by: 'occurred_at', order: 'desc' },
    refreshMs,
  );
  const activeQuery = useAlerts(
    { page: 1, page_size: 10, status: 'active', sort_by: 'occurred_at', order: 'desc' },
    refreshMs,
  );
  const tracksQuery = useTracks({
    page: 1,
    page_size: SAMPLE,
    sort_by: 'first_seen',
    order: 'desc',
  });
  const violationsQuery = useViolations({ page: 1, page_size: SAMPLE });
  const eventsQuery = useSystemEvents(
    { page: 1, page_size: 8, sort_by: 'occurred_at', order: 'desc' },
    refreshMs,
  );
  const streamQuery = useStreamStatus();

  const alerts = useMemo(() => alertsQuery.data?.items ?? [], [alertsQuery.data]);
  const tracks = useMemo(() => tracksQuery.data?.items ?? [], [tracksQuery.data]);
  const violations = useMemo(() => violationsQuery.data?.items ?? [], [violationsQuery.data]);

  return useMemo(() => {
    const hourly = alertsByHour(alerts);
    const series = hourly.map((bucket) => bucket.total);
    const stream = streamQuery.data;

    return {
      summary: summariseAlerts(alerts),
      severity: severityDistribution(alerts),
      categories: categoryDistribution(alerts),
      rules: ruleDistribution(alerts),
      hourly,
      occupancy: occupancyTrend(tracks),
      dwell: dwellByClass(tracks),
      // Prefer violations for zone attribution — they carry per-frame
      // zone metadata; fall back to alerts when none are loaded.
      zones: zoneViolations(violations.length > 0 ? violations : alerts),

      recentAlerts: alerts.slice(0, 8),
      activeAlerts: activeQuery.data?.items ?? [],
      recentEvents: eventsQuery.data?.items ?? [],
      tracks,

      workers: workerCount(tracks),
      totalAlerts: alertsQuery.data?.meta.total ?? 0,
      totalViolations: violationsQuery.data?.meta.total ?? 0,
      fps: stream?.publish_fps ?? null,
      // The API reports no GPU utilisation metric. Frame rate against a
      // 30 fps target is the closest honest proxy for how loaded the
      // inference device is, and is labelled as such in the UI.
      gpuUtilisation: stream?.publish_fps ? Math.min(1, stream.publish_fps / 30) : null,
      device: stream?.device ?? null,

      alertSeries: series,
      alertDelta: periodDelta(series),

      isLoading: alertsQuery.isLoading,
      isFetching:
        alertsQuery.isFetching ||
        activeQuery.isFetching ||
        tracksQuery.isFetching ||
        eventsQuery.isFetching,
      error: (alertsQuery.error as Error | null) ?? null,
      refetch: () => {
        void alertsQuery.refetch();
        void activeQuery.refetch();
        void tracksQuery.refetch();
        void violationsQuery.refetch();
        void eventsQuery.refetch();
        void streamQuery.refetch();
      },
    };
  }, [
    alerts,
    tracks,
    violations,
    alertsQuery,
    activeQuery,
    tracksQuery,
    violationsQuery,
    eventsQuery,
    streamQuery,
  ]);
}
