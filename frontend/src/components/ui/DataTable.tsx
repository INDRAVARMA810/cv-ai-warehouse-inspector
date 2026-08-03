import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react';
import type { Column, PageMeta, SortState } from '@/types';
import { cn } from '@/utils/cn';
import { TableSkeleton } from './Skeleton';
import { EmptyState, ErrorState } from './States';
import { Pagination } from './Pagination';

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  /** Stable React key for a row. */
  rowKey: (row: T) => string | number;

  isLoading?: boolean;
  /** True during a background refetch; dims the body without unmounting it. */
  isFetching?: boolean;
  error?: unknown;
  onRetry?: () => void;

  sort?: SortState;
  onSort?: (key: string) => void;

  meta?: PageMeta;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;

  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyDescription?: string;
  className?: string;
}

/**
 * Reusable table with sorting, pagination and full state handling.
 *
 * Owns no data fetching and no formatting: columns supply their own
 * renderers, and the parent supplies rows plus query state. That keeps
 * every list page consistent while leaving business logic outside.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  isLoading = false,
  isFetching = false,
  error,
  onRetry,
  sort,
  onSort,
  meta,
  onPageChange,
  onPageSizeChange,
  onRowClick,
  emptyTitle = 'No records found',
  emptyDescription = 'Try widening your filters or clearing the search term.',
  className,
}: DataTableProps<T>) {
  if (error) {
    return <ErrorState error={error} onRetry={onRetry} />;
  }

  if (isLoading) {
    return <TableSkeleton rows={8} columns={columns.length} />;
  }

  if (rows.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className={cn('flex flex-col', className)}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[52rem] border-collapse text-sm">
          <thead>
            <tr className="border-b border-surface-700/70 text-left">
              {columns.map((column) => {
                const isSorted = sort?.sortBy === column.key;
                const sortable = Boolean(column.sortable && onSort);

                return (
                  <th
                    key={column.key}
                    scope="col"
                    aria-sort={
                      isSorted ? (sort?.order === 'asc' ? 'ascending' : 'descending') : undefined
                    }
                    className={cn(
                      'whitespace-nowrap px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-content-muted',
                      column.hideOnMobile && 'hidden md:table-cell',
                      column.className,
                    )}
                  >
                    {sortable ? (
                      <button
                        type="button"
                        onClick={() => onSort?.(column.key)}
                        className={cn(
                          'inline-flex items-center gap-1.5 rounded transition-colors hover:text-content-primary',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50',
                          isSorted && 'text-accent',
                        )}
                      >
                        {column.header}
                        {isSorted ? (
                          sort?.order === 'asc' ? (
                            <ArrowUp className="h-3 w-3" />
                          ) : (
                            <ArrowDown className="h-3 w-3" />
                          )
                        ) : (
                          <ChevronsUpDown className="h-3 w-3 opacity-40" />
                        )}
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody
            className={cn(
              'divide-y divide-surface-700/50 transition-opacity duration-200',
              isFetching && 'opacity-50',
            )}
          >
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  'transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-surface-800/70',
                )}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cn(
                      'px-4 py-3 align-middle text-content-secondary',
                      column.hideOnMobile && 'hidden md:table-cell',
                      column.className,
                    )}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {meta && onPageChange ? (
        <Pagination meta={meta} onPageChange={onPageChange} onPageSizeChange={onPageSizeChange} />
      ) : null}
    </div>
  );
}
