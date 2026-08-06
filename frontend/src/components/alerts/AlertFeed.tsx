import { ChevronRight, TrendingUp } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Alert } from '@/types';
import { formatDateTime, formatRelative, truncate } from '@/utils/format';
import { categoryLabel, levelTone } from '@/utils/severity';
import { cn } from '@/utils/cn';
import { EmptyState, ErrorState, LevelBadge, ListSkeleton, StatusBadge } from '@/components/ui';

interface AlertFeedProps {
  alerts: Alert[];
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  emptyTitle?: string;
  emptyDescription?: string;
  /** Renders the empty state as good news. */
  emptyPositive?: boolean;
  /** Shows the lifecycle status pill alongside severity. */
  showStatus?: boolean;
  onSelect?: (alert: Alert) => void;
}

/**
 * Compact alert list.
 *
 * Used where density matters more than the full column set of the table.
 * A coloured severity rail on the left edge lets the list be scanned by
 * colour position alone, before any text is read.
 */
export function AlertFeed({
  alerts,
  isLoading = false,
  error,
  onRetry,
  emptyTitle = 'No alerts',
  emptyDescription,
  emptyPositive = false,
  showStatus = false,
  onSelect,
}: AlertFeedProps) {
  if (error) return <ErrorState error={error} onRetry={onRetry} compact className="m-3" />;
  if (isLoading) return <ListSkeleton rows={5} />;

  if (alerts.length === 0) {
    return (
      <EmptyState title={emptyTitle} description={emptyDescription} positive={emptyPositive} />
    );
  }

  return (
    <ul>
      {alerts.map((alert, index) => {
        const tone = levelTone(alert.level);

        return (
          <li key={alert.alert_id}>
            <button
              type="button"
              onClick={() => onSelect?.(alert)}
              disabled={!onSelect}
              style={{ animationDelay: `${Math.min(index, 10) * 25}ms` }}
              className={cn(
                'group flex w-full animate-row-in items-start gap-2.5 border-b border-edge-soft px-3 py-2.5 text-left',
                'transition-colors duration-150',
                tone.rail,
                onSelect ? 'hover:bg-panel-raised' : 'cursor-default',
              )}
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <LevelBadge level={alert.level} live={alert.status === 'active'} />
                  {showStatus ? <StatusBadge status={alert.status} /> : null}
                  {alert.was_escalated ? (
                    <span
                      className="inline-flex items-center gap-0.5 font-mono text-2xs text-warn"
                      title={`Escalated from ${alert.initial_level}`}
                    >
                      <TrendingUp className="h-3 w-3" />
                      ESC
                    </span>
                  ) : null}
                </div>

                <p className="mt-1 text-xs leading-snug text-ink">
                  {truncate(alert.message, 80)}
                </p>

                <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 font-mono text-2xs text-ink-ghost">
                  <span title={formatDateTime(alert.occurred_at)}>
                    {formatRelative(alert.occurred_at)}
                  </span>
                  <span className="text-ink-ghost/60">·</span>
                  <span>{categoryLabel(alert.category)}</span>
                  {alert.track_id !== null ? (
                    <>
                      <span className="text-ink-ghost/60">·</span>
                      <span className="tabular">#{alert.track_id}</span>
                    </>
                  ) : null}
                  {alert.occurrence_count > 1 ? (
                    <>
                      <span className="text-ink-ghost/60">·</span>
                      <span className="tabular">×{alert.occurrence_count}</span>
                    </>
                  ) : null}
                </p>
              </div>

              {onSelect ? (
                <ChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-ink-ghost opacity-0 transition-opacity group-hover:opacity-100" />
              ) : null}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/** Footer link through to the full, filterable table. */
export function AlertFeedFooter({ to, label }: { to: string; label: string }) {
  return (
    <div className="border-t border-edge bg-panel-rail/40 px-3 py-1.5">
      <Link
        to={to}
        className="inline-flex items-center gap-1 text-2xs font-medium text-info transition-colors hover:text-info/80"
      >
        {label}
        <ChevronRight className="h-3 w-3" />
      </Link>
    </div>
  );
}
