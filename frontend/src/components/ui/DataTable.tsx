import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react';
import type { Column, PageMeta, SortState } from '@/types';
import { cn } from '@/utils/cn';
import { TableSkeleton } from './Skeleton';
import { EmptyState, ErrorState } from './States';
import { Pagination } from './Pagination';

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;

  isLoading?: boolean;
  /** True during a background refetch; dims the body without unmounting. */
  isFetching?: boolean;
  error?: unknown;
  onRetry?: () => void;

  sort?: SortState;
  onSort?: (key: string) => void;

  meta?: PageMeta;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;

  onRowClick?: (row: T) => void;
  /** Left status rail class per row, e.g. from a tone. */
  rowRail?: (row: T) => string | undefined;
  emptyTitle?: string;
  emptyDescription?: string;
  /** Renders the empty state as good news. */
  emptyPositive?: boolean;
  className?: string;
}

/**
 * Dense operational table.
 *
 * Rows are compact with hairline separators and an optional left status
 * rail, so severity is readable by colour position alone before any text
 * is parsed. Owns no fetching and no formatting: columns supply their
 * own renderers and the parent supplies query state.
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
  rowRail,
  emptyTitle = 'No records',
  emptyDescription = 'Widen the filters or clear the search term.',
  emptyPositive = false,
  className,
}: DataTableProps<T>) {
  if (error) return <ErrorState error={error} onRetry={onRetry} />;
  if (isLoading) return <TableSkeleton rows={8} columns={columns.length} />;

  if (rows.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        positive={emptyPositive}
      />
    );
  }

  return (
    <div className={cn('flex flex-col', className)}>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[48rem] border-collapse text-xs">
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-edge bg-panel-rail/90 backdrop-blur-sm">
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
                      'whitespace-nowrap px-3 py-2 text-left text-2xs font-semibold uppercase tracking-[0.12em] text-ink-faint',
                      column.hideOnMobile && 'hidden md:table-cell',
                      column.className,
                    )}
                  >
                    {sortable ? (
                      <button
                        type="button"
                        onClick={() => onSort?.(column.key)}
                        className={cn(
                          'inline-flex items-center gap-1 rounded-control transition-colors hover:text-ink',
                          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-info/60',
                          isSorted && 'text-info',
                        )}
                      >
                        {column.header}
                        {isSorted ? (
                          sort?.order === 'asc' ? (
                            <ArrowUp className="h-2.5 w-2.5" />
                          ) : (
                            <ArrowDown className="h-2.5 w-2.5" />
                          )
                        ) : (
                          <ChevronsUpDown className="h-2.5 w-2.5 opacity-30" />
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
              'transition-opacity duration-200',
              isFetching && 'opacity-45',
            )}
          >
            {rows.map((row, index) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                style={{ animationDelay: `${Math.min(index, 12) * 14}ms` }}
                className={cn(
                  'animate-row-in border-b border-edge-soft transition-colors duration-150',
                  rowRail?.(row),
                  onRowClick && 'cursor-pointer hover:bg-panel-raised',
                )}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={cn(
                      'px-3 py-2 align-middle text-ink-dim',
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
