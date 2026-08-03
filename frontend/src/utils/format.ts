/** Presentation helpers for dates, numbers and identifiers. */

const DATE_TIME = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: 'short',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

const TIME_ONLY = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

const RELATIVE = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });

/** Parse an ISO timestamp, tolerating null and malformed input. */
function toDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Format an absolute timestamp, e.g. "03 Aug 2026, 14:22:07". */
export function formatDateTime(value: string | null | undefined): string {
  const date = toDate(value);
  return date ? DATE_TIME.format(date) : '—';
}

/** Format only the clock time, for dense table columns. */
export function formatTime(value: string | null | undefined): string {
  const date = toDate(value);
  return date ? TIME_ONLY.format(date) : '—';
}

/**
 * Format a timestamp relative to now, e.g. "12 minutes ago".
 *
 * Operators care far more about recency than wall-clock time, so this
 * is the primary rendering in lists; the absolute value is kept in a
 * tooltip.
 */
export function formatRelative(value: string | null | undefined): string {
  const date = toDate(value);
  if (!date) return '—';

  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const abs = Math.abs(seconds);

  if (abs < 45) return 'just now';
  if (abs < 3600) return RELATIVE.format(Math.round(seconds / 60), 'minute');
  if (abs < 86_400) return RELATIVE.format(Math.round(seconds / 3600), 'hour');
  if (abs < 2_592_000) return RELATIVE.format(Math.round(seconds / 86_400), 'day');
  return RELATIVE.format(Math.round(seconds / 2_592_000), 'month');
}

/** Format a duration in seconds as a compact "1h 04m 12s". */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds) || seconds < 0) return '—';
  if (seconds < 1) return '<1s';

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')}m`;
  if (minutes > 0) return `${minutes}m ${String(secs).padStart(2, '0')}s`;
  return `${secs}s`;
}

/** Elapsed seconds between two ISO timestamps. */
export function durationBetween(
  from: string | null | undefined,
  to: string | null | undefined,
): number | null {
  const start = toDate(from);
  const end = toDate(to);
  if (!start || !end) return null;
  return (end.getTime() - start.getTime()) / 1000;
}

/** Group thousands, e.g. 12400 -> "12,400". */
export function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat().format(value);
}

/** Render a 0–1 confidence as a percentage. */
export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

/** Shorten a UUID to its first segment for dense display. */
export function shortId(value: string | null | undefined, length = 8): string {
  if (!value) return '—';
  return value.length <= length ? value : value.slice(0, length);
}

/** Convert a snake_case identifier into "Title Case". */
export function humanise(value: string | null | undefined): string {
  if (!value) return '—';
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

/** Truncate text to a maximum length, adding an ellipsis. */
export function truncate(value: string, max = 90): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}
