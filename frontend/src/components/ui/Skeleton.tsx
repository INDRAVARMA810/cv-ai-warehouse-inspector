import type { ComponentPropsWithoutRef } from 'react';
import { cn } from '@/utils/cn';

/**
 * Loading placeholder.
 *
 * A directional sweep rather than a fade — it reads as data arriving on
 * an instrument, and makes it obvious the interface is working rather
 * than frozen. Mirrors the shape of the content it replaces so nothing
 * shifts when real values land.
 */
export function Skeleton({ className, ...rest }: ComponentPropsWithoutRef<'div'>) {
  return (
    <div
      aria-hidden
      {...rest}
      className={cn(
        'relative overflow-hidden rounded-control bg-edge-soft',
        'after:absolute after:inset-0 after:-translate-x-full after:animate-sweep',
        'after:bg-gradient-to-r after:from-transparent after:via-white/[0.05] after:to-transparent',
        className,
      )}
    />
  );
}

/** Placeholder matching the KPI grid. */
export function StatSkeleton() {
  return (
    <div className="rounded-panel border border-edge bg-panel p-3.5">
      <Skeleton className="h-2.5 w-20" />
      <Skeleton className="mt-3.5 h-8 w-24" />
      <Skeleton className="mt-3 h-2.5 w-28" />
    </div>
  );
}

/** Placeholder matching a data table, header row included. */
export function TableSkeleton({ rows = 8, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <div role="status" aria-label="Loading table data">
      <div className="flex gap-4 border-b border-edge px-3 py-2">
        {Array.from({ length: columns }).map((_, index) => (
          <Skeleton key={index} className="h-2.5 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div
          key={rowIndex}
          className="flex items-center gap-4 border-b border-edge-soft px-3 py-2.5"
          style={{ opacity: 1 - rowIndex * 0.07 }}
        >
          {Array.from({ length: columns }).map((_, columnIndex) => (
            <Skeleton
              key={columnIndex}
              className={cn('h-3 flex-1', columnIndex === 0 && 'max-w-[5rem]')}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Placeholder matching a chart panel. */
export function ChartSkeleton({ height = 220 }: { height?: number }) {
  return (
    <div
      className="flex items-end gap-1.5 p-4"
      style={{ height }}
      role="status"
      aria-label="Loading chart"
    >
      {Array.from({ length: 16 }).map((_, index) => (
        <Skeleton
          key={index}
          className="flex-1 rounded-t-sm"
          style={{ height: `${25 + ((index * 41) % 70)}%` }}
        />
      ))}
    </div>
  );
}

/** Placeholder matching a feed of rows. */
export function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading list">
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="flex items-center gap-3 border-b border-edge-soft px-4 py-3"
          style={{ opacity: 1 - index * 0.12 }}
        >
          <Skeleton className="h-7 w-1 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-3 w-3/5" />
            <Skeleton className="h-2.5 w-2/5" />
          </div>
          <Skeleton className="h-4 w-14 shrink-0" />
        </div>
      ))}
    </div>
  );
}
