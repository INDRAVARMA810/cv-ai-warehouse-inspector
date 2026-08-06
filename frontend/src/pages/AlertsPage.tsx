import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FilterX, Siren } from 'lucide-react';
import { useAlert, useAlerts, useTableQuery } from '@/hooks';
import type {
  Alert,
  AlertCategory,
  AlertLevel,
  AlertStatus,
  Column,
  SelectOption,
} from '@/types';
import { ALERT_CATEGORIES, ALERT_LEVELS, ALERT_STATUSES } from '@/types';
import { AppLayout } from '@/components/layout';
import {
  Button,
  DataTable,
  Field,
  LevelBadge,
  Panel,
  PanelHeader,
  SearchInput,
  Select,
  StatusBadge,
} from '@/components/ui';
import { AlertDetail } from '@/components/alerts/AlertDetail';
import { categoryLabel } from '@/utils/severity';
import { formatDateTime, formatRelative, humanise, truncate } from '@/utils/format';

interface AlertFilters {
  status?: AlertStatus;
  level?: AlertLevel;
  category?: AlertCategory;
}

const INITIAL_FILTERS: AlertFilters = {};

const STATUS_OPTIONS: SelectOption<AlertStatus>[] = ALERT_STATUSES.map((value) => ({
  value,
  label: humanise(value),
}));
const LEVEL_OPTIONS: SelectOption<AlertLevel>[] = ALERT_LEVELS.map((value) => ({
  value,
  label: humanise(value),
}));
const CATEGORY_OPTIONS: SelectOption<AlertCategory>[] = ALERT_CATEGORIES.map((value) => ({
  value,
  label: categoryLabel(value),
}));

/**
 * Full alert register.
 *
 * Query state lives in `useTableQuery`; data comes from `useAlerts`.
 * The page itself only declares columns and wires the pieces together.
 */
export function AlertsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = useState<Alert | null>(null);

  const table = useTableQuery<AlertFilters>(INITIAL_FILTERS, {
    initialSortBy: 'occurred_at',
    initialPageSize: 25,
  });

  const { setFilter } = table;

  // Honour a status supplied by a dashboard deep-link, once.
  const statusParam = searchParams.get('status') as AlertStatus | null;
  useEffect(() => {
    if (statusParam && ALERT_STATUSES.includes(statusParam)) {
      setFilter('status', statusParam);
    }
  }, [statusParam, setFilter]);

  // A `focus` param opens that alert's detail panel directly.
  const focusId = searchParams.get('focus');
  const focused = useAlert(focusId);
  useEffect(() => {
    if (focused.data) setSelected(focused.data);
  }, [focused.data]);

  const query = useAlerts({
    page: table.page,
    page_size: table.pageSize,
    sort_by: table.sort.sortBy,
    order: table.sort.order,
    search: table.search || undefined,
    ...table.filters,
  });

  const columns = useMemo<Column<Alert>[]>(
    () => [
      {
        key: 'level',
        header: 'Severity',
        sortable: true,
        render: (row) => <LevelBadge level={row.level} />,
      },
      {
        key: 'occurred_at',
        header: 'Raised',
        sortable: true,
        render: (row) => (
          <span title={formatDateTime(row.occurred_at)} className="whitespace-nowrap">
            {formatRelative(row.occurred_at)}
          </span>
        ),
      },
      {
        key: 'message',
        header: 'Incident',
        className: 'w-full',
        render: (row) => (
          <span className="text-ink">{truncate(row.message, 78)}</span>
        ),
      },
      {
        key: 'rule_name',
        header: 'Rule',
        sortable: true,
        hideOnMobile: true,
        render: (row) => (
          <span className="whitespace-nowrap">{humanise(row.rule_name.replace(/Rule$/, ''))}</span>
        ),
      },
      {
        key: 'category',
        header: 'Category',
        sortable: true,
        hideOnMobile: true,
        render: (row) => (
          <span className="whitespace-nowrap">{categoryLabel(row.category)}</span>
        ),
      },
      {
        key: 'track_id',
        header: 'Track',
        sortable: true,
        hideOnMobile: true,
        render: (row) => (
          <span className="font-mono">{row.track_id !== null ? `#${row.track_id}` : '—'}</span>
        ),
      },
      {
        key: 'occurrence_count',
        header: 'Seen',
        sortable: true,
        hideOnMobile: true,
        render: (row) => <span className="font-mono tabular">{row.occurrence_count}</span>,
      },
      {
        key: 'status',
        header: 'Status',
        sortable: true,
        render: (row) => <StatusBadge status={row.status} />,
      },
    ],
    [],
  );

  const clearAll = () => {
    table.resetFilters();
    setSearchParams({}, { replace: true });
  };

  return (
    <AppLayout
      title="Alerts"
      subtitle="Safety incident register"
      onRefresh={() => void query.refetch()}
      isRefreshing={query.isFetching}
    >
      <Panel>
        <PanelHeader
          title="Alert Register"
          subtitle={
            query.data
              ? `${query.data.meta.total} incident${query.data.meta.total === 1 ? '' : 's'} matching`
              : 'Loading incidents…'
          }
          icon={<Siren className="h-4 w-4" />}
          actions={
            table.hasActiveFilters ? (
              <Button size="sm" variant="ghost" icon={<FilterX className="h-3.5 w-3.5" />} onClick={clearAll}>
                Clear
              </Button>
            ) : null
          }
        />

        <div className="grid grid-cols-1 gap-3 border-b border-edge p-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Search" className="sm:col-span-2 lg:col-span-1">
            <SearchInput
              value={table.searchInput}
              onValueChange={table.setSearchInput}
              placeholder="Message or rule…"
            />
          </Field>
          <Field label="Status">
            <Select
              value={table.filters.status ?? ''}
              options={STATUS_OPTIONS}
              onValueChange={(value) => table.setFilter('status', value)}
              placeholder="All statuses"
            />
          </Field>
          <Field label="Severity">
            <Select
              value={table.filters.level ?? ''}
              options={LEVEL_OPTIONS}
              onValueChange={(value) => table.setFilter('level', value)}
              placeholder="All severities"
            />
          </Field>
          <Field label="Category">
            <Select
              value={table.filters.category ?? ''}
              options={CATEGORY_OPTIONS}
              onValueChange={(value) => table.setFilter('category', value)}
              placeholder="All categories"
            />
          </Field>
        </div>

        <DataTable
          columns={columns}
          rows={query.data?.items ?? []}
          rowKey={(row) => row.alert_id}
          isLoading={query.isLoading}
          isFetching={query.isFetching}
          error={query.error}
          onRetry={() => void query.refetch()}
          sort={table.sort}
          onSort={table.toggleSort}
          meta={query.data?.meta}
          onPageChange={table.setPage}
          onPageSizeChange={table.setPageSize}
          onRowClick={setSelected}
          emptyTitle="No alerts match these filters"
          emptyDescription="Widen the severity or status filter, or clear the search term."
        />
      </Panel>

      <AlertDetail
        alert={selected}
        onClose={() => {
          setSelected(null);
          if (focusId) {
            searchParams.delete('focus');
            setSearchParams(searchParams, { replace: true });
          }
        }}
      />
    </AppLayout>
  );
}
