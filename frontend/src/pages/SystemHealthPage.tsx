import { useMemo } from 'react';
import { Activity, AlertOctagon, FilterX, Info, ScrollText, TriangleAlert } from 'lucide-react';
import { useHealth, useSystemEvents, useTableQuery } from '@/hooks';
import type { Column, SelectOption, SystemEvent } from '@/types';
import { AppLayout } from '@/components/layout';
import {
  Button,
  DataTable,
  EventLevelBadge,
  Field,
  Panel,
  PanelHeader,
  SearchInput,
  Select,
  StatCard,
  StatSkeleton,
} from '@/components/ui';
import { SystemStatusPanel } from '@/components/dashboard';
import { formatDateTime, formatRelative, humanise, truncate } from '@/utils/format';
import { eventLevelCounts } from '@/utils/stats';

interface EventFilters {
  level?: string;
}

const INITIAL_FILTERS: EventFilters = {};

const LEVEL_OPTIONS: SelectOption<string>[] = [
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'error', label: 'Error' },
  { value: 'critical', label: 'Critical' },
];

/**
 * Platform health and the operational event log.
 *
 * Pairs current component status with the event history behind it —
 * "degraded" is only actionable next to the events that caused it.
 */
export function SystemHealthPage() {
  const health = useHealth();

  const table = useTableQuery<EventFilters>(INITIAL_FILTERS, {
    initialSortBy: 'occurred_at',
    initialPageSize: 25,
  });

  const query = useSystemEvents(
    {
      page: table.page,
      page_size: table.pageSize,
      sort_by: table.sort.sortBy,
      order: table.sort.order,
      search: table.search || undefined,
      ...table.filters,
    },
    20_000,
  );

  // Counts describe the visible page, which is what the table shows.
  const counts = useMemo(
    () => eventLevelCounts(query.data?.items ?? []),
    [query.data],
  );

  const columns = useMemo<Column<SystemEvent>[]>(
    () => [
      {
        key: 'level',
        header: 'Level',
        sortable: true,
        render: (row) => <EventLevelBadge level={row.level} />,
      },
      {
        key: 'occurred_at',
        header: 'When',
        sortable: true,
        render: (row) => (
          <span title={formatDateTime(row.occurred_at)} className="whitespace-nowrap">
            {formatRelative(row.occurred_at)}
          </span>
        ),
      },
      {
        key: 'event_type',
        header: 'Event',
        sortable: true,
        render: (row) => (
          <span className="whitespace-nowrap font-medium text-content-primary">
            {humanise(row.event_type)}
          </span>
        ),
      },
      {
        key: 'message',
        header: 'Message',
        className: 'w-full',
        render: (row) => <span>{truncate(row.message, 82)}</span>,
      },
      {
        key: 'source',
        header: 'Source',
        sortable: true,
        hideOnMobile: true,
        render: (row) => (
          <span className="whitespace-nowrap font-mono text-xs text-content-muted">
            {row.source ?? '—'}
          </span>
        ),
      },
    ],
    [],
  );

  return (
    <AppLayout
      title="System Health"
      subtitle="Platform status and operational events"
      onRefresh={() => {
        void health.refetch();
        void query.refetch();
      }}
      isRefreshing={health.isFetching || query.isFetching}
    >
      <div className="space-y-5">
        <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">
          <SystemStatusPanel
            health={health.data}
            isLoading={health.isLoading}
            isError={health.isError}
          />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 xl:col-span-2">
            {query.isLoading ? (
              Array.from({ length: 3 }).map((_, index) => <StatSkeleton key={index} />)
            ) : (
              <>
                <StatCard
                  label="Events (page)"
                  value={query.data?.items.length ?? 0}
                  icon={<ScrollText className="h-4 w-4" />}
                  tone="accent"
                  hint={`${query.data?.meta.total ?? 0} recorded in total`}
                />
                <StatCard
                  label="Warnings"
                  value={counts.warning ?? 0}
                  icon={<TriangleAlert className="h-4 w-4" />}
                  tone={(counts.warning ?? 0) > 0 ? 'warning' : 'neutral'}
                  emphasise={(counts.warning ?? 0) > 0}
                  hint="On the visible page"
                />
                <StatCard
                  label="Errors"
                  value={(counts.error ?? 0) + (counts.critical ?? 0)}
                  icon={<AlertOctagon className="h-4 w-4" />}
                  tone={(counts.error ?? 0) + (counts.critical ?? 0) > 0 ? 'danger' : 'success'}
                  emphasise={(counts.error ?? 0) + (counts.critical ?? 0) > 0}
                  hint="On the visible page"
                />
              </>
            )}
          </div>
        </section>

        <Panel>
          <PanelHeader
            title="Event Log"
            description={
              query.data
                ? `${query.data.meta.total} event${query.data.meta.total === 1 ? '' : 's'} recorded`
                : 'Loading events…'
            }
            icon={<Activity className="h-4 w-4" />}
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
                placeholder="Message or event type…"
              />
            </Field>
            <Field label="Level">
              <Select
                value={table.filters.level ?? ''}
                options={LEVEL_OPTIONS}
                onValueChange={(value) => table.setFilter('level', value)}
                placeholder="All levels"
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
            emptyTitle="No events match these filters"
            emptyDescription="The pipeline records events as it starts, stops and encounters problems."
          />
        </Panel>

        <p className="flex items-start gap-2 px-1 text-xs text-content-muted">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Health is polled every 15 seconds and the event log every 20. Warning and error counts
          describe the currently visible page, not the whole log.
        </p>
      </div>
    </AppLayout>
  );
}
