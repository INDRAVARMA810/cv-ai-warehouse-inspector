import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { PageMeta } from '@/types';
import { formatNumber } from '@/utils/format';
import { cn } from '@/utils/cn';
import { Button } from './Button';

interface PaginationProps {
  meta: PageMeta;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
}

/**
 * Page navigation driven by the API's own pagination metadata.
 *
 * `has_next` / `has_previous` come from the backend rather than being
 * recomputed here, so the controls cannot disagree with the server
 * about whether another page exists.
 */
export function Pagination({
  meta,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
}: PaginationProps) {
  const firstRow = meta.total === 0 ? 0 : (meta.page - 1) * meta.page_size + 1;
  const lastRow = Math.min(meta.page * meta.page_size, meta.total);

  return (
    <div className="flex flex-col gap-3 border-t border-surface-700/70 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-content-muted">
        Showing{' '}
        <span className="font-mono text-content-secondary">
          {formatNumber(firstRow)}–{formatNumber(lastRow)}
        </span>{' '}
        of <span className="font-mono text-content-secondary">{formatNumber(meta.total)}</span>
      </p>

      <div className="flex items-center gap-3">
        {onPageSizeChange ? (
          <label className="flex items-center gap-2 text-xs text-content-muted">
            <span className="hidden sm:inline">Rows</span>
            <select
              value={meta.page_size}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
              className="h-8 cursor-pointer rounded-lg border border-surface-600 bg-surface-800 px-2 text-xs text-content-primary focus:border-accent/60 focus:outline-none"
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="secondary"
            disabled={!meta.has_previous}
            onClick={() => onPageChange(meta.page - 1)}
            icon={<ChevronLeft className="h-3.5 w-3.5" />}
            aria-label="Previous page"
          >
            <span className="hidden sm:inline">Prev</span>
          </Button>

          <span className="px-1 text-xs text-content-muted">
            Page <span className="font-mono text-content-secondary">{meta.page}</span>
            {' / '}
            <span className="font-mono text-content-secondary">{Math.max(1, meta.pages)}</span>
          </span>

          <Button
            size="sm"
            variant="secondary"
            disabled={!meta.has_next}
            onClick={() => onPageChange(meta.page + 1)}
            className={cn('flex-row-reverse')}
            icon={<ChevronRight className="h-3.5 w-3.5" />}
            aria-label="Next page"
          >
            <span className="hidden sm:inline">Next</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
