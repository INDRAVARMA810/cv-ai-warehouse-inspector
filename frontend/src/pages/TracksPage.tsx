import { useMemo } from 'react';
import { FilterX, Radar } from 'lucide-react';
import { useTableQuery, useTracks } from '@/hooks';
import type { Column, Track } from '@/types';
import { AppLayout } from '@/components/layout';
import {
  Badge,
  Button,
  DataTable,
  Field,
  Panel,
  PanelHeader,
  SearchInput,
  Select,
} from '@/components/ui';
import {
  durationBetween,
  formatDateTime,
  formatDuration,
  formatPercent,
  formatRelative,
} from '@/utils/format';
import { cn } from '@/utils/cn';

interface TrackFilters {
  min_observations?: number;
}

const INITIAL_FILTERS: TrackFilters = {};

/** Dwell thresholds, expressed as observation counts. */
const OBSERVATION_OPTIONS = [
  { value: '10', label: '10+ frames' },
  { value: '50', label: '50+ frames' },
  { value: '100', label: '100+ frames' },
  { value: '500', label: '500+ frames' },
] as const;

/**
 * Tracked-object register.
 *
 * One row per identity per appearance, summarising where and for how
 * long an object was observed — the basis for dwell-time analysis.
 */
export function TracksPage() {
  const table = useTableQuery<TrackFilters>(INITIAL_FILTERS, {
    initialSortBy: 'first_seen',
    initialPageSize: 25,
  });

  const query = useTracks({
    page: table.page,
    page_size: table.pageSize,
    sort_by: table.sort.sortBy,
    order: table.sort.order,
    search: table.search || undefined,
    ...table.filters,
  });

  const columns = useMemo<Column<Track>[]>(
    () => [
      {
        key: 'track_id',
        header: 'Track',
        sortable: true,
        render: (row) => (
          <span className="font-mono font-medium text-content-primary">#{row.track_id}</span>
        ),
      },
      {
        key: 'class_name',
        header: 'Class',
        sortable: true,
        render: (row) => <Badge className="capitalize">{row.class_name}</Badge>,
      },
      {
        key: 'confidence',
        header: 'Confidence',
        sortable: true,
        hideOnMobile: true,
        render: (row) => <ConfidenceBar value={row.confidence} />,
      },
      {
        key: 'observation_count',
        header: 'Frames',
        sortable: true,
        render: (row) => (
          <span className="font-mono tabular-nums">{row.observation_count}</span>
        ),
      },
      {
        key: 'duration',
        header: 'Dwell',
        hideOnMobile: true,
        render: (row) => (
          <span className="whitespace-nowrap font-mono tabular-nums">
            {formatDuration(durationBetween(row.first_seen, row.last_seen))}
          </span>
        ),
      },
      {
        key: 'first_seen',
        header: 'First seen',
        sortable: true,
        render: (row) => (
          <span title={formatDateTime(row.first_seen)} className="whitespace-nowrap">
            {formatRelative(row.first_seen)}
          </span>
        ),
      },
      {
        key: 'last_seen',
        header: 'Last seen',
        sortable: true,
        hideOnMobile: true,
        render: (row) => (
          <span title={formatDateTime(row.last_seen)} className="whitespace-nowrap">
            {formatRelative(row.last_seen)}
          </span>
        ),
      },
    ],
    [],
  );

  return (
    <AppLayout
      title="Tracks"
      subtitle="Detected object lifetimes"
      onRefresh={() => void query.refetch()}
      isRefreshing={query.isFetching}
    >
      <Panel>
        <PanelHeader
          title="Tracked Objects"
          description={
            query.data
              ? `${query.data.meta.total} track${query.data.meta.total === 1 ? '' : 's'} recorded`
              : 'Loading tracks…'
          }
          icon={<Radar className="h-4 w-4" />}
          actions={
            table.hasActiveFilters ? (
              <Button
                size="sm"
                variant="ghost"
                icon={<FilterX className="h-3.5 w-3.5" />}
                onClick={table.resetFilters}
              >
                Clear
              </Button>
            ) : null
          }
        />

        <div className="grid grid-cols-1 gap-3 border-b border-surface-700/70 p-4 sm:grid-cols-3">
          <Field label="Search" className="sm:col-span-2">
            <SearchInput
              value={table.searchInput}
              onValueChange={table.setSearchInput}
              placeholder="Object class…"
            />
          </Field>
          <Field label="Minimum dwell">
            <Select
              value={table.filters.min_observations ? String(table.filters.min_observations) : ''}
              options={[...OBSERVATION_OPTIONS]}
              onValueChange={(value) =>
                table.setFilter('min_observations', value ? Number(value) : undefined)
              }
              placeholder="Any duration"
            />
          </Field>
        </div>

        <DataTable
          columns={columns}
          rows={query.data?.items ?? []}
          rowKey={(row) => row.id}
          isLoading={query.isLoading}
          isFetching={query.isFetching}
          error={query.error}
          onRetry={() => void query.refetch()}
          sort={table.sort}
          onSort={table.toggleSort}
          meta={query.data?.meta}
          onPageChange={table.setPage}
          onPageSizeChange={table.setPageSize}
          emptyTitle="No tracks match these filters"
          emptyDescription="Tracks are recorded as the tracker assigns identities to detected objects."
        />
      </Panel>
    </AppLayout>
  );
}

/** Confidence as a compact bar plus its numeric value. */
function ConfidenceBar({ value }: { value: number | null }) {
  if (value == null) return <span className="text-content-muted">—</span>;

  const percent = Math.max(0, Math.min(1, value)) * 100;
  const tone =
    percent >= 80 ? 'bg-emerald-400' : percent >= 55 ? 'bg-amber-400' : 'bg-rose-400';

  return (
    <span className="flex items-center gap-2">
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-surface-700">
        <span className={cn('block h-full rounded-full', tone)} style={{ width: `${percent}%` }} />
      </span>
      <span className="font-mono tabular-nums text-xs">{formatPercent(value, 0)}</span>
    </span>
  );
}
