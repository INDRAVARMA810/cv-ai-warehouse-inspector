/**
 * Domain vocabulary → presentation mapping.
 *
 * Centralising this means severity colour is defined once. A component
 * never decides what "critical" looks like, and the charts, badges and
 * table rows cannot drift apart.
 */

import type { AlertCategory, AlertLevel, AlertStatus } from '@/types';

interface Tone {
  /** Text colour class. */
  text: string;
  /** Translucent background for pills and row highlights. */
  bg: string;
  /** Border colour for outlined elements. */
  border: string;
  /** Solid colour for chart marks, where classes do not apply. */
  hex: string;
  label: string;
}

const LEVEL_TONES: Record<AlertLevel, Tone> = {
  info: {
    text: 'text-sky-300',
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/30',
    hex: '#38BDF8',
    label: 'Info',
  },
  low: {
    text: 'text-cyan-300',
    bg: 'bg-cyan-500/10',
    border: 'border-cyan-500/30',
    hex: '#22D3EE',
    label: 'Low',
  },
  medium: {
    text: 'text-amber-300',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    hex: '#FBBF24',
    label: 'Medium',
  },
  high: {
    text: 'text-rose-300',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    hex: '#FB7185',
    label: 'High',
  },
  critical: {
    text: 'text-red-300',
    bg: 'bg-red-500/15',
    border: 'border-red-500/40',
    hex: '#EF4444',
    label: 'Critical',
  },
};

const STATUS_TONES: Record<AlertStatus, Tone> = {
  active: {
    text: 'text-rose-300',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    hex: '#FB7185',
    label: 'Active',
  },
  acknowledged: {
    text: 'text-amber-300',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    hex: '#FBBF24',
    label: 'Acknowledged',
  },
  resolved: {
    text: 'text-emerald-300',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    hex: '#34D399',
    label: 'Resolved',
  },
  expired: {
    text: 'text-slate-400',
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/30',
    hex: '#64748B',
    label: 'Expired',
  },
};

const FALLBACK_TONE: Tone = {
  text: 'text-content-secondary',
  bg: 'bg-surface-700/40',
  border: 'border-surface-600',
  hex: '#64748B',
  label: 'Unknown',
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

/** Presentation tone for an alert urgency level. */
export function levelTone(level: string | null | undefined): Tone {
  if (!level) return FALLBACK_TONE;
  return LEVEL_TONES[level as AlertLevel] ?? FALLBACK_TONE;
}

/** Presentation tone for an alert lifecycle status. */
export function statusTone(status: string | null | undefined): Tone {
  if (!status) return FALLBACK_TONE;
  return STATUS_TONES[status as AlertStatus] ?? FALLBACK_TONE;
}

/**
 * Presentation tone for a system-event level.
 *
 * System events use logging vocabulary (`warning`, `error`) rather than
 * alert vocabulary, so they are mapped onto the same visual scale here.
 */
export function eventLevelTone(level: string | null | undefined): Tone {
  switch ((level ?? '').toLowerCase()) {
    case 'critical':
    case 'fatal':
      return LEVEL_TONES.critical;
    case 'error':
      return LEVEL_TONES.high;
    case 'warning':
    case 'warn':
      return LEVEL_TONES.medium;
    case 'info':
      return LEVEL_TONES.info;
    case 'debug':
      return FALLBACK_TONE;
    default:
      return FALLBACK_TONE;
  }
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
