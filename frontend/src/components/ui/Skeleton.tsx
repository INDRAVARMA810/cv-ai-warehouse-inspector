import type { ComponentPropsWithoutRef } from 'react';
import { cn } from '@/utils/cn';

type SkeletonProps = ComponentPropsWithoutRef<'div'>;

/**
 * Shimmering placeholder shown while data loads.
 *
 * Skeletons mirror the shape of the content they replace so the layout
 * does not shift when real data arrives.
 *
 * Accepts every intrinsic `div` prop rather than a hand-picked subset:
 * callers routinely need `style` for computed dimensions, and `id` or
 * `data-*` for testing. Enumerating props one at a time invites the
 * caller and the component to drift apart.
 *
 * Marked `aria-hidden` by default — a skeleton is decorative, and the
 * loading state is announced by the surrounding region.
 */
export function Skeleton({ className, ...rest }: SkeletonProps) {
  return (
    <div
      aria-hidden
      {...rest}
      className={cn(
        'relative overflow-hidden rounded-md bg-surface-750/70',
        'after:absolute after:inset-0 after:-translate-x-full after:animate-shimmer',
        'after:bg-gradient-to-r after:from-transparent after:via-white/[0.06] after:to-transparent',
        className,
      )}
    />
  );
}

/** Placeholder matching the stat-tile grid. */
export function StatSkeleton() {
  return (
    <div className="rounded-xl border border-surface-700/70 bg-surface-850/80 p-5">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-4 h-8 w-20" />
      <Skeleton className="mt-3 h-3 w-32" />
    </div>
  );
}

/** Placeholder matching the data table, including its header row. */
export function TableSkeleton({ rows = 8, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div className="divide-y divide-surface-700/60" role="status" aria-label="Loading table data">
      <div className="flex gap-4 px-5 py-3">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} className="h-3 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex items-center gap-4 px-5 py-3.5">
          {Array.from({ length: columns }).map((_, columnIndex) => (
            <Skeleton
              key={columnIndex}
              className={cn('h-4 flex-1', columnIndex === 0 && 'max-w-[7rem]')}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Placeholder matching a chart panel. */
export function ChartSkeleton({ height = 240 }: { height?: number }) {
  return (
    <div
      className="flex items-end gap-2 p-5"
      style={{ height }}
      role="status"
      aria-label="Loading chart"
    >
      {Array.from({ length: 12 }).map((_, index) => (
        <Skeleton
          key={index}
          className="flex-1 rounded-t-md"
          // Deterministic varied heights read as a chart rather than a block.
          style={{ height: `${30 + ((index * 37) % 65)}%` }}
        />
      ))}
    </div>
  );
}

/** Placeholder for a list of text lines, e.g. an activity feed. */
export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3 p-5" role="status" aria-label="Loading list">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center gap-3">
          <Skeleton className="h-8 w-8 shrink-0 rounded-lg" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-3 w-3/5" />
            <Skeleton className="h-2.5 w-2/5" />
          </div>
        </div>
      ))}
    </div>
  );
}
