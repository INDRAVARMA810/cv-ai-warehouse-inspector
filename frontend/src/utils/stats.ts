/**
 * Derived statistics for the dashboard.
 *
 * Aggregation lives here rather than in components so the maths is
 * testable in isolation and the same figures can back both a stat tile
 * and a chart without being computed twice, differently.
 */

import type { Alert, AlertLevel, SeverityDatum, SystemEvent } from '@/types';
import { levelTone } from './severity';

/** Count alerts per urgency level, preserving severity order. */
export function severityDistribution(alerts: Alert[]): SeverityDatum[] {
  const order: AlertLevel[] = ['critical', 'high', 'medium', 'low', 'info'];
  const counts = new Map<AlertLevel, number>();

  for (const alert of alerts) {
    counts.set(alert.level, (counts.get(alert.level) ?? 0) + 1);
  }

  return order
    .map((level) => {
      const tone = levelTone(level);
      return { level, label: tone.label, value: counts.get(level) ?? 0, color: tone.hex };
    })
    .filter((datum) => datum.value > 0);
}

/** Count alerts per hazard category, highest first. */
export function categoryDistribution(
  alerts: Alert[],
): Array<{ name: string; value: number }> {
  const counts = new Map<string, number>();

  for (const alert of alerts) {
    counts.set(alert.category, (counts.get(alert.category) ?? 0) + 1);
  }

  return [...counts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

/** Count alerts per originating rule, highest first. */
export function ruleDistribution(
  alerts: Alert[],
  limit = 6,
): Array<{ name: string; value: number }> {
  const counts = new Map<string, number>();

  for (const alert of alerts) {
    counts.set(alert.rule_name, (counts.get(alert.rule_name) ?? 0) + 1);
  }

  return [...counts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

export interface TrendPoint {
  /** Bucket start, as an ISO string. */
  timestamp: string;
  /** Short axis label. */
  label: string;
  total: number;
  critical: number;
  high: number;
}

/**
 * Bucket alerts into a fixed number of equal time intervals.
 *
 * Empty buckets are retained so the trend line shows quiet periods
 * rather than silently compressing them, which would misrepresent the
 * rate of incidents.
 */
export function alertTrend(alerts: Alert[], buckets = 12, hours = 24): TrendPoint[] {
  const now = Date.now();
  const windowMs = hours * 3_600_000;
  const bucketMs = windowMs / buckets;
  const start = now - windowMs;

  const points: TrendPoint[] = Array.from({ length: buckets }, (_, index) => {
    const bucketStart = start + index * bucketMs;
    return {
      timestamp: new Date(bucketStart).toISOString(),
      label: new Date(bucketStart).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }),
      total: 0,
      critical: 0,
      high: 0,
    };
  });

  for (const alert of alerts) {
    const time = new Date(alert.occurred_at).getTime();
    if (Number.isNaN(time) || time < start || time > now) continue;

    const index = Math.min(buckets - 1, Math.floor((time - start) / bucketMs));
    const point = points[index];
    point.total += 1;
    if (alert.level === 'critical') point.critical += 1;
    if (alert.level === 'high') point.high += 1;
  }

  return points;
}

export interface AlertSummary {
  total: number;
  active: number;
  acknowledged: number;
  resolved: number;
  critical: number;
  escalated: number;
  /** Sum of every alert's observation count. */
  observations: number;
}

/** Summarise a set of alerts into the figures shown as stat tiles. */
export function summariseAlerts(alerts: Alert[]): AlertSummary {
  return alerts.reduce<AlertSummary>(
    (summary, alert) => ({
      total: summary.total + 1,
      active: summary.active + (alert.status === 'active' ? 1 : 0),
      acknowledged: summary.acknowledged + (alert.status === 'acknowledged' ? 1 : 0),
      resolved: summary.resolved + (alert.status === 'resolved' ? 1 : 0),
      critical: summary.critical + (alert.level === 'critical' ? 1 : 0),
      escalated: summary.escalated + (alert.was_escalated ? 1 : 0),
      observations: summary.observations + alert.occurrence_count,
    }),
    {
      total: 0,
      active: 0,
      acknowledged: 0,
      resolved: 0,
      critical: 0,
      escalated: 0,
      observations: 0,
    },
  );
}

/** Count system events by severity level. */
export function eventLevelCounts(events: SystemEvent[]): Record<string, number> {
  return events.reduce<Record<string, number>>((counts, event) => {
    const key = event.level.toLowerCase();
    counts[key] = (counts[key] ?? 0) + 1;
    return counts;
  }, {});
}
