import { History } from 'lucide-react';
import type { SystemEvent } from '@/types';
import { formatDateTime, formatRelative, humanise, truncate } from '@/utils/format';
import { eventLevelTone } from '@/utils/severity';
import { cn } from '@/utils/cn';
import {
  EmptyState,
  ErrorState,
  ListSkeleton,
  Panel,
  PanelHeader,
} from '@/components/ui';

interface ActivityFeedProps {
  events: SystemEvent[];
  isLoading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  className?: string;
}

/**
 * Operational event timeline.
 *
 * Provides the "why" behind gaps in coverage — a dropped frame or a
 * stopped pipeline explains an otherwise suspiciously quiet alert feed,
 * and without it an operator can mistake an outage for a safe shift.
 */
export function ActivityFeed({
  events,
  isLoading = false,
  error,
  onRetry,
  className,
}: ActivityFeedProps) {
  return (
    <Panel className={cn('flex flex-col overflow-hidden', className)}>
      <PanelHeader
        title="Recent Activity"
        subtitle="System event log"
        icon={<History className="h-3.5 w-3.5" />}
      />

      {error ? (
        <ErrorState error={error} onRetry={onRetry} />
      ) : isLoading ? (
        <ListSkeleton rows={5} />
      ) : events.length === 0 ? (
        <EmptyState
          title="No recent activity"
          description="Events appear here as the pipeline starts, stops and encounters faults."
        />
      ) : (
        <ol className="flex-1 px-3 py-2.5">
          {events.map((event, index) => {
            const tone = eventLevelTone(event.level);
            const isLast = index === events.length - 1;

            return (
              <li
                key={event.id}
                className="relative flex gap-2.5 pb-3 last:pb-0 animate-row-in"
                style={{ animationDelay: `${index * 30}ms` }}
              >
                {!isLast ? (
                  <span aria-hidden className="absolute left-[3px] top-3 h-full w-px bg-edge" />
                ) : null}

                <span
                  className="relative mt-1 h-[7px] w-[7px] shrink-0 rounded-full ring-4 ring-panel"
                  style={{ backgroundColor: tone.hex }}
                />

                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 text-xs font-medium leading-tight text-ink">
                    <span className="truncate">{humanise(event.event_type)}</span>
                    <span className={cn('shrink-0 font-mono text-2xs uppercase', tone.text)}>
                      {event.level}
                    </span>
                  </p>
                  <p className="mt-0.5 truncate text-2xs text-ink-faint">
                    {truncate(event.message, 68)}
                  </p>
                  <p
                    className="mt-0.5 font-mono text-2xs text-ink-ghost"
                    title={formatDateTime(event.occurred_at)}
                  >
                    {formatRelative(event.occurred_at)}
                    {event.source ? ` · ${event.source}` : ''}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </Panel>
  );
}
