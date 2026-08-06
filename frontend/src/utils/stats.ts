/**
 * Derived statistics for the dashboard.
 *
 * Aggregation lives here rather than in components so the maths is
 * testable in isolation, and so a stat tile and the chart beside it are
 * always computed from the same function rather than two similar-looking
 * ones that can drift.
 *
 * The backend exposes no aggregate endpoints, so every figure is derived
 * client-side from a recent page of records. That makes these *sample*
 * statistics: exact totals always come from the API's `meta.total`.
 */

import type { Alert, AlertLevel, SeverityDatum, SystemEvent, Track, Violation } from '@/types';
import { categoryLabel, levelTone } from './severity';
import { durationBetween } from './format';

/* ------------------------------------------------------------------ */
/* Alert distributions                                                 */
/* ------------------------------------------------------------------ */

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
export function categoryDistribution(alerts: Alert[]): Array<{ name: string; value: number }> {
  const counts = new Map<string, number>();
  for (const alert of alerts) {
    counts.set(alert.category, (counts.get(alert.category) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, value]) => ({ name: categoryLabel(name), value }))
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

/* ------------------------------------------------------------------ */
/* Time series                                                         */
/* ------------------------------------------------------------------ */

export interface HourBucket {
  /** Axis label, e.g. "14:00". */
  label: string;
  hour: number;
  total: number;
  critical: number;
  high: number;
  other: number;
}

/**
 * Alerts bucketed by clock hour over a trailing window.
 *
 * Empty hours are retained so quiet periods stay visible — dropping them
 * would compress the axis and misrepresent the incident rate.
 */
export function alertsByHour(alerts: Alert[], hours = 24): HourBucket[] {
  const now = new Date();
  const buckets: HourBucket[] = [];

  for (let offset = hours - 1; offset >= 0; offset -= 1) {
    const slot = new Date(now.getTime() - offset * 3_600_000);
    buckets.push({
      label: `${String(slot.getHours()).padStart(2, '0')}:00`,
      hour: slot.getHours(),
      total: 0,
      critical: 0,
      high: 0,
      other: 0,
    });
  }

  const windowStart = now.getTime() - hours * 3_600_000;

  for (const alert of alerts) {
    const time = new Date(alert.occurred_at).getTime();
    if (Number.isNaN(time) || time < windowStart || time > now.getTime()) continue;

    const index = Math.min(
      buckets.length - 1,
      Math.floor((time - windowStart) / 3_600_000),
    );
    const bucket = buckets[index];
    bucket.total += 1;
    if (alert.level === 'critical') bucket.critical += 1;
    else if (alert.level === 'high') bucket.high += 1;
    else bucket.other += 1;
  }

  return buckets;
}

export interface OccupancyPoint {
  label: string;
  timestamp: string;
  /** Distinct tracked objects active in this bucket. */
  occupancy: number;
  people: number;
}

/**
 * Occupancy over time, inferred from track lifetimes.
 *
 * A track counts toward a bucket when its observed lifetime overlaps
 * that bucket, which approximates how many objects were on the floor
 * at that moment.
 */
export function occupancyTrend(tracks: Track[], buckets = 16, hours = 8): OccupancyPoint[] {
  const now = Date.now();
  const windowMs = hours * 3_600_000;
  const bucketMs = windowMs / buckets;
  const start = now - windowMs;

  return Array.from({ length: buckets }, (_, index) => {
    const from = start + index * bucketMs;
    const to = from + bucketMs;

    let occupancy = 0;
    let people = 0;

    for (const track of tracks) {
      const first = new Date(track.first_seen).getTime();
      const last = track.last_seen ? new Date(track.last_seen).getTime() : first;
      if (Number.isNaN(first)) continue;
      // Overlap test between the track's lifetime and this bucket.
      if (last >= from && first <= to) {
        occupancy += 1;
        if (track.class_name.toLowerCase() === 'person') people += 1;
      }
    }

    return {
      timestamp: new Date(from).toISOString(),
      label: new Date(from).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }),
      occupancy,
      people,
    };
  });
}

/* ------------------------------------------------------------------ */
/* Zones and dwell                                                     */
/* ------------------------------------------------------------------ */

/**
 * Violations grouped by the zone named in their metadata.
 *
 * Zone-scoped rules record `zone_name`; rules with no spatial component
 * do not, so those are grouped under "Unzoned" rather than dropped —
 * hiding them would understate total violation volume.
 */
export function zoneViolations(
  records: Array<Violation | Alert>,
): Array<{ zone: string; total: number; critical: number; color: string }> {
  const counts = new Map<string, { total: number; critical: number }>();

  for (const record of records) {
    const zone = (record.metadata?.zone_name as string | undefined) ?? 'Unzoned';
    const entry = counts.get(zone) ?? { total: 0, critical: 0 };
    entry.total += 1;

    const level = 'severity' in record ? record.severity : record.level;
    if (level === 'critical') entry.critical += 1;

    counts.set(zone, entry);
  }

  return [...counts.entries()]
    .map(([zone, entry]) => ({
      zone,
      total: entry.total,
      critical: entry.critical,
      // A zone is coloured by whether it has produced critical events.
      color: entry.critical > 0 ? '#EF4444' : entry.total > 0 ? '#F59E0B' : '#3B82F6',
    }))
    .sort((a, b) => b.total - a.total);
}

export interface DwellDatum {
  className: string;
  /** Mean dwell time in seconds. */
  average: number;
  /** Longest observed dwell in seconds. */
  peak: number;
  samples: number;
}

/**
 * Mean and peak dwell time per object class.
 *
 * Dwell is the span between a track's first and last sighting. Tracks
 * with no `last_seen` are skipped rather than counted as zero, which
 * would drag every average down.
 */
export function dwellByClass(tracks: Track[]): DwellDatum[] {
  const groups = new Map<string, number[]>();

  for (const track of tracks) {
    const seconds = durationBetween(track.first_seen, track.last_seen);
    if (seconds === null || seconds <= 0) continue;

    const list = groups.get(track.class_name) ?? [];
    list.push(seconds);
    groups.set(track.class_name, list);
  }

  return [...groups.entries()]
    .map(([className, values]) => ({
      className,
      average: values.reduce((sum, value) => sum + value, 0) / values.length,
      peak: Math.max(...values),
      samples: values.length,
    }))
    .sort((a, b) => b.average - a.average);
}

/* ------------------------------------------------------------------ */
/* Summaries                                                           */
/* ------------------------------------------------------------------ */

export interface AlertSummary {
  total: number;
  active: number;
  acknowledged: number;
  resolved: number;
  critical: number;
  high: number;
  escalated: number;
  observations: number;
  /** Alerts raised since local midnight. */
  today: number;
}

/** Summarise a set of alerts into the figures shown as KPI tiles. */
export function summariseAlerts(alerts: Alert[]): AlertSummary {
  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  const midnightMs = midnight.getTime();

  return alerts.reduce<AlertSummary>(
    (summary, alert) => {
      const occurred = new Date(alert.occurred_at).getTime();
      return {
        total: summary.total + 1,
        active: summary.active + (alert.status === 'active' ? 1 : 0),
        acknowledged: summary.acknowledged + (alert.status === 'acknowledged' ? 1 : 0),
        resolved: summary.resolved + (alert.status === 'resolved' ? 1 : 0),
        critical: summary.critical + (alert.level === 'critical' ? 1 : 0),
        high: summary.high + (alert.level === 'high' ? 1 : 0),
        escalated: summary.escalated + (alert.was_escalated ? 1 : 0),
        observations: summary.observations + alert.occurrence_count,
        today: summary.today + (!Number.isNaN(occurred) && occurred >= midnightMs ? 1 : 0),
      };
    },
    {
      total: 0,
      active: 0,
      acknowledged: 0,
      resolved: 0,
      critical: 0,
      high: 0,
      escalated: 0,
      observations: 0,
      today: 0,
    },
  );
}

/** Distinct people currently on the floor, from recent tracks. */
export function workerCount(tracks: Track[], withinSeconds = 900): number {
  const cutoff = Date.now() - withinSeconds * 1000;
  const ids = new Set<number>();

  for (const track of tracks) {
    if (track.class_name.toLowerCase() !== 'person') continue;
    const last = new Date(track.last_seen ?? track.first_seen).getTime();
    if (!Number.isNaN(last) && last >= cutoff) ids.add(track.track_id);
  }

  return ids.size;
}

/** Count system events by severity level. */
export function eventLevelCounts(events: SystemEvent[]): Record<string, number> {
  return events.reduce<Record<string, number>>((counts, event) => {
    const key = event.level.toLowerCase();
    counts[key] = (counts[key] ?? 0) + 1;
    return counts;
  }, {});
}

/**
 * Percentage change between the newer and older half of a series.
 *
 * Returns `null` when either half is empty, so a tile shows no delta
 * rather than a misleading "+100%" derived from a single data point.
 */
export function periodDelta(values: number[]): number | null {
  if (values.length < 4) return null;

  const midpoint = Math.floor(values.length / 2);
  const older = values.slice(0, midpoint);
  const newer = values.slice(midpoint);

  const sum = (list: number[]) => list.reduce((total, value) => total + value, 0);
  const olderTotal = sum(older);
  const newerTotal = sum(newer);

  if (olderTotal === 0) return newerTotal === 0 ? 0 : null;
  return ((newerTotal - olderTotal) / olderTotal) * 100;
}
