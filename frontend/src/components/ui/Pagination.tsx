import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { PageMeta } from '@/types';
import { formatNumber } from '@/utils/format';
import { IconButton } from './Button';

interface PaginationProps {
  meta: PageMeta;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  pageSizeOptions?: number[];
}

/**
 * Page navigation driven by the API's own pagination metadata.
 *
 * `has_next` / `has_previous` come from the server rather than being
 * recomputed here, so the controls cannot disagree with it about whether
 * another page exists.
 */
export function Pagination({
  meta,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [25, 50, 100, 200],
}: PaginationProps) {
  const first = meta.total === 0 ? 0 : (meta.page - 1) * meta.page_size + 1;
  const last = Math.min(meta.page * meta.page_size, meta.total);

  return (
    <div className="flex flex-col gap-2 border-t border-edge bg-panel-rail/40 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
      <p className="font-mono text-2xs tabular text-ink-faint">
        <span className="text-ink-dim">
          {formatNumber(first)}–{formatNumber(last)}
        </span>
        {' / '}
        <span className="text-ink-dim">{formatNumber(meta.total)}</span>
        <span className="ml-1.5 text-ink-ghost">rows</span>
      </p>

      <div className="flex items-center gap-2.5">
        {onPageSizeChange ? (
          <label className="flex items-center gap-1.5 text-2xs text-ink-ghost">
            <span className="hidden sm:inline uppercase tracking-wider">Page size</span>
            <select
              value={meta.page_size}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
              className="h-6 cursor-pointer rounded-control border border-edge bg-panel-inset px-1.5 font-mono text-2xs tabular text-ink-dim transition-colors hover:border-edge-strong focus:border-info/60 focus:outline-none"
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <div className="flex items-center gap-1">
          <IconButton
            size="sm"
            label="Previous page"
            variant="secondary"
            disabled={!meta.has_previous}
            onClick={() => onPageChange(meta.page - 1)}
            icon={<ChevronLeft className="h-3.5 w-3.5" />}
          />
          <span className="px-1 font-mono text-2xs tabular text-ink-faint">
            <span className="text-ink-dim">{meta.page}</span>
            {' / '}
            {Math.max(1, meta.pages)}
          </span>
          <IconButton
            size="sm"
            label="Next page"
            variant="secondary"
            disabled={!meta.has_next}
            onClick={() => onPageChange(meta.page + 1)}
            icon={<ChevronRight className="h-3.5 w-3.5" />}
          />
        </div>
      </div>
    </div>
  );
}
