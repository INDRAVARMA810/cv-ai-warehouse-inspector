import { History } from 'lucide-react';
import type { SystemEvent } from '@/types';
import { formatDateTime, formatRelative, humanise } from '@/utils/format';
import { eventLevelTone } from '@/utils/severity';
import { cn } from '@/utils/cn';
import { EmptyState, ListSkeleton, Panel, PanelHeader } from '@/components/ui';

interface ActivityFeedProps {
  events: SystemEvent[];
  isLoading?: boolean;
}

/**
 * Recent operational events as a vertical timeline.
 *
 * Gives the "why" behind gaps in detection coverage — a dropped camera
 * frame or a stopped pipeline explains an otherwise suspiciously quiet
 * alert feed.
 */
export function ActivityFeed({ events, isLoading = false }: ActivityFeedProps) {
  return (
    <Panel className="flex h-full flex-col">
      <PanelHeader
        title="Recent Activity"
        description="System events"
        icon={<History className="h-4 w-4" />}
      />

      {isLoading ? (
        <ListSkeleton rows={5} />
      ) : events.length === 0 ? (
        <EmptyState
          title="No recent activity"
          description="System events will appear here as the pipeline runs."
          className="py-10"
        />
      ) : (
        <ol className="flex-1 px-5 py-4">
          {events.map((event, index) => {
            const tone = eventLevelTone(event.level);
            const isLast = index === events.length - 1;

            return (
              <li key={event.id} className="relative flex gap-3 pb-4 last:pb-0">
                {!isLast ? (
                  <span
                    aria-hidden
                    className="absolute left-[5px] top-4 h-full w-px bg-surface-700"
                  />
                ) : null}

                <span
                  className={cn('relative mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ring-4 ring-surface-850', tone.bg)}
                  style={{ backgroundColor: tone.hex }}
                />

                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 text-sm font-medium leading-tight text-content-primary">
                    <span className="truncate">{humanise(event.event_type)}</span>
                    <span className={cn('shrink-0 text-[10px] uppercase', tone.text)}>
                      {event.level}
                    </span>
                  </p>
                  <p className="mt-0.5 truncate text-xs text-content-secondary">{event.message}</p>
                  <p className="mt-0.5 text-[11px] text-content-muted" title={formatDateTime(event.occurred_at)}>
                    {formatRelative(event.occurred_at)}
                    {event.source ? <span className="font-mono"> · {event.source}</span> : null}
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
