/**
 * Domain vocabulary → presentation mapping.
 *
 * The palette is four signals only — emerald (safe), amber (warning),
 * red (critical), blue (information). Emerald is reserved for genuinely
 * good states: it never appears on a severity level, because a "low"
 * alert is still an alert. Severity therefore runs blue → amber → red,
 * and emerald is kept for resolved, healthy and compliant.
 *
 * Centralising this means a component never decides what "critical"
 * looks like, so badges, rails, charts and rows cannot drift apart.
 */

import type { AlertCategory, AlertLevel, AlertStatus } from '@/types';

export interface Tone {
  /** Foreground text colour class. */
  text: string;
  /** Translucent fill for pills and row washes. */
  bg: string;
  /** Border colour for outlined elements. */
  border: string;
  /** Left status rail, applied to table rows and list items. */
  rail: string;
  /** Solid hex for chart marks and inline SVG, where classes cannot reach. */
  hex: string;
  /** LED / dot colour class. */
  dot: string;
  label: string;
}

const BLUE: Omit<Tone, 'label'> = {
  text: 'text-info',
  bg: 'bg-info/10',
  border: 'border-info/30',
  rail: 'shadow-rail-info',
  hex: '#3B82F6',
  dot: 'bg-info',
};

const AMBER: Omit<Tone, 'label'> = {
  text: 'text-warn',
  bg: 'bg-warn/10',
  border: 'border-warn/30',
  rail: 'shadow-rail-warn',
  hex: '#F59E0B',
  dot: 'bg-warn',
};

const RED: Omit<Tone, 'label'> = {
  text: 'text-crit',
  bg: 'bg-crit/12',
  border: 'border-crit/35',
  rail: 'shadow-rail-crit',
  hex: '#EF4444',
  dot: 'bg-crit',
};

const EMERALD: Omit<Tone, 'label'> = {
  text: 'text-safe',
  bg: 'bg-safe/10',
  border: 'border-safe/30',
  rail: 'shadow-rail-safe',
  hex: '#10B981',
  dot: 'bg-safe',
};

const NEUTRAL: Omit<Tone, 'label'> = {
  text: 'text-ink-faint',
  bg: 'bg-edge-soft',
  border: 'border-edge',
  rail: '',
  hex: '#5E6873',
  dot: 'bg-ink-ghost',
};

/**
 * Severity ramp.
 *
 * `high` uses the same red family as `critical` but at reduced weight —
 * both demand attention, and splitting them across two hues would imply
 * a difference in kind rather than degree.
 */
const LEVEL_TONES: Record<AlertLevel, Tone> = {
  info: { ...BLUE, label: 'Info' },
  low: { ...BLUE, text: 'text-info/80', label: 'Low' },
  medium: { ...AMBER, label: 'Medium' },
  high: { ...RED, text: 'text-crit/85', bg: 'bg-crit/10', label: 'High' },
  critical: { ...RED, label: 'Critical' },
};

const STATUS_TONES: Record<AlertStatus, Tone> = {
  active: { ...RED, label: 'Active' },
  acknowledged: { ...AMBER, label: 'Acknowledged' },
  resolved: { ...EMERALD, label: 'Resolved' },
  expired: { ...NEUTRAL, label: 'Expired' },
};

const CATEGORY_LABELS: Record<AlertCategory, string> = {
  zone_intrusion: 'Zone Intrusion',
  proximity: 'Proximity',
  occupancy: 'Occupancy',
  ppe: 'PPE',
  equipment: 'Equipment',
  system: 'System',
  other: 'Other',
};

const FALLBACK: Tone = { ...NEUTRAL, label: 'Unknown' };

/** Presentation tone for an alert urgency level. */
export function levelTone(level: string | null | undefined): Tone {
  if (!level) return FALLBACK;
  return LEVEL_TONES[level as AlertLevel] ?? FALLBACK;
}

/** Presentation tone for an alert lifecycle status. */
export function statusTone(status: string | null | undefined): Tone {
  if (!status) return FALLBACK;
  return STATUS_TONES[status as AlertStatus] ?? FALLBACK;
}

/**
 * Presentation tone for a system-event level.
 *
 * System events speak logging vocabulary (`warning`, `error`) rather
 * than alert vocabulary, so they are mapped onto the same visual scale.
 */
export function eventLevelTone(level: string | null | undefined): Tone {
  switch ((level ?? '').toLowerCase()) {
    case 'critical':
    case 'fatal':
    case 'error':
      return { ...RED, label: 'Error' };
    case 'warning':
    case 'warn':
      return { ...AMBER, label: 'Warning' };
    case 'info':
      return { ...BLUE, label: 'Info' };
    case 'debug':
      return FALLBACK;
    default:
      return FALLBACK;
  }
}

/** Tone for a boolean healthy/unhealthy component. */
export function healthTone(healthy: boolean): Tone {
  return healthy
    ? { ...EMERALD, label: 'Operational' }
    : { ...RED, label: 'Fault' };
}

/** Human-readable label for a hazard category. */
export function categoryLabel(category: string | null | undefined): string {
  if (!category) return 'Unknown';
  return CATEGORY_LABELS[category as AlertCategory] ?? 'Other';
}

/** Numeric rank so levels can be compared or sorted. */
export function levelRank(level: string | null | undefined): number {
  const order: AlertLevel[] = ['info', 'low', 'medium', 'high', 'critical'];
  const index = order.indexOf((level ?? '') as AlertLevel);
  return index === -1 ? -1 : index;
}

/** Whether a level warrants prominent, attention-grabbing treatment. */
export function isUrgent(level: string | null | undefined): boolean {
  return levelRank(level) >= levelRank('high');
}
