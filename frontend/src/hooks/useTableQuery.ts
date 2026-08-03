import { useCallback, useMemo, useState } from 'react';
import type { SortOrder, SortState } from '@/types';
import { useDebounce } from './useDebounce';

interface TableQueryOptions {
  initialPageSize?: number;
  initialSortBy?: string;
  initialOrder?: SortOrder;
}

interface TableQueryState<F> {
  page: number;
  pageSize: number;
  sort: SortState;
  /** Raw search text, bound directly to the input. */
  searchInput: string;
  /** Debounced search text, safe to send to the API. */
  search: string;
  filters: F;

  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setSearchInput: (value: string) => void;
  /** Toggle sort direction, or switch to a new column descending-first. */
  toggleSort: (key: string) => void;
  /** Merge filter changes and reset to the first page. */
  setFilter: <K extends keyof F>(key: K, value: F[K]) => void;
  resetFilters: () => void;
  /** Whether any filter or search term is currently applied. */
  hasActiveFilters: boolean;
}

/**
 * Shared state for a filterable, sortable, paginated table.
 *
 * Every list page needs the same behaviour: debounce the search box,
 * reset to page 1 whenever the result set changes shape, and flip sort
 * direction on repeated clicks. Keeping it in one hook means the pages
 * stay declarative and cannot drift apart in these details.
 */
export function useTableQuery<F extends object>(
  // `object` rather than `Record<string, unknown>`: TypeScript
  // interfaces have no implicit index signature, so the stricter
  // constraint would reject every caller that declares its filters as
  // an interface.
  initialFilters: F,
  options: TableQueryOptions = {},
): TableQueryState<F> {
  const { initialPageSize = 25, initialSortBy, initialOrder = 'desc' } = options;

  const [page, setPageState] = useState(1);
  const [pageSize, setPageSizeState] = useState(initialPageSize);
  const [sort, setSort] = useState<SortState>({ sortBy: initialSortBy, order: initialOrder });
  const [searchInput, setSearchInputState] = useState('');
  const [filters, setFilters] = useState<F>(initialFilters);

  const search = useDebounce(searchInput, 350);

  const setPage = useCallback((next: number) => setPageState(Math.max(1, next)), []);

  const setPageSize = useCallback((size: number) => {
    setPageSizeState(size);
    // A different page size makes the current page number meaningless.
    setPageState(1);
  }, []);

  const setSearchInput = useCallback((value: string) => {
    setSearchInputState(value);
    setPageState(1);
  }, []);

  const toggleSort = useCallback((key: string) => {
    setSort((current) =>
      current.sortBy === key
        ? { sortBy: key, order: current.order === 'desc' ? 'asc' : 'desc' }
        : { sortBy: key, order: 'desc' },
    );
    setPageState(1);
  }, []);

  const setFilter = useCallback(<K extends keyof F>(key: K, value: F[K]) => {
    setFilters((current) => ({ ...current, [key]: value }));
    setPageState(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(initialFilters);
    setSearchInputState('');
    setPageState(1);
    // Intentionally keyed on the initial filters identity supplied by
    // the caller, which is expected to be a stable module constant.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const hasActiveFilters = useMemo(
    () =>
      searchInput.trim().length > 0 ||
      Object.values(filters).some((value) => value !== undefined && value !== '' && value !== null),
    [filters, searchInput],
  );

  return {
    page,
    pageSize,
    sort,
    searchInput,
    search,
    filters,
    setPage,
    setPageSize,
    setSearchInput,
    toggleSort,
    setFilter,
    resetFilters,
    hasActiveFilters,
  };
}
