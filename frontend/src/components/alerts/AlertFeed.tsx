import { ArrowUpRight, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Alert } from '@/types';
import { formatRelative, formatDateTime, truncate } from '@/utils/format';
import { categoryLabel, levelTone } from '@/utils/severity';
import { cn } from '@/utils/cn';
import { EmptyState, LevelBadge, ListSkeleton, StatusBadge } from '@/components/ui';

interface AlertFeedProps {
  alerts: Alert[];
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  /** Shows the lifecycle status pill alongside the level. */
  showStatus?: boolean;
  onSelect?: (alert: Alert) => void;
}

/**
 * Compact vertical list of alerts.
 *
 * Used for the dashboard feeds, where density matters more than the
 * full column set of the table. A coloured rail on the left encodes
 * severity so the list can be scanned without reading any text.
 */
export function AlertFeed({
  alerts,
  isLoading = false,
  emptyTitle = 'No alerts',
  emptyDescription,
  showStatus = false,
  onSelect,
}: AlertFeedProps) {
  if (isLoading) return <ListSkeleton rows={5} />;

  if (alerts.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} className="py-10" />;
  }

  return (
    <ul className="divide-y divide-surface-700/50">
      {alerts.map((alert) => {
        const tone = levelTone(alert.level);

        return (
          <li key={alert.alert_id}>
            <button
              type="button"
              onClick={() => onSelect?.(alert)}
              disabled={!onSelect}
              className={cn(
                'group flex w-full items-start gap-3 px-5 py-3.5 text-left transition-colors',
                onSelect ? 'hover:bg-surface-800/70' : 'cursor-default',
              )}
            >
              <span
                className={cn('mt-1 h-9 w-1 shrink-0 rounded-full')}
                style={{ backgroundColor: tone.hex }}
                aria-hidden
              />

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <LevelBadge level={alert.level} />
                  {showStatus ? <StatusBadge status={alert.status} /> : null}
                  {alert.was_escalated ? (
                    <span className="inline-flex items-center gap-1 text-[11px] text-amber-300">
                      <TrendingUp className="h-3 w-3" />
                      escalated
                    </span>
                  ) : null}
                </div>

                <p className="mt-1.5 text-sm leading-snug text-content-primary">
                  {truncate(alert.message, 96)}
                </p>

                <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-content-muted">
                  <span title={formatDateTime(alert.occurred_at)}>
                    {formatRelative(alert.occurred_at)}
                  </span>
                  <span className="font-mono">{categoryLabel(alert.category)}</span>
                  {alert.track_id !== null ? (
                    <span className="font-mono">track #{alert.track_id}</span>
                  ) : null}
                  {alert.occurrence_count > 1 ? (
                    <span className="font-mono">×{alert.occurrence_count}</span>
                  ) : null}
                </p>
              </div>

              {onSelect ? (
                <ArrowUpRight className="mt-1 h-4 w-4 shrink-0 text-content-muted opacity-0 transition-opacity group-hover:opacity-100" />
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** Footer link sending the operator to the full, filterable table. */
export function AlertFeedFooter({ to, label }: { to: string; label: string }) {
  return (
    <div className="border-t border-surface-700/70 px-5 py-3">
      <Link
        to={to}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-accent transition-colors hover:text-accent/80"
      >
        {label}
        <ArrowUpRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  );
}
