import { useMemo } from 'react';
import { FilterX, ShieldAlert } from 'lucide-react';
import { useTableQuery, useViolations } from '@/hooks';
import type { AlertLevel, Column, SelectOption, Violation } from '@/types';
import { ALERT_LEVELS } from '@/types';
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
} from '@/components/ui';
import { formatDateTime, formatRelative, humanise, shortId, truncate } from '@/utils/format';

interface ViolationFilters {
  severity?: AlertLevel;
}

const INITIAL_FILTERS: ViolationFilters = {};

const SEVERITY_OPTIONS: SelectOption<AlertLevel>[] = ALERT_LEVELS.map((value) => ({
  value,
  label: humanise(value),
}));

/**
 * Raw rule violations — the per-frame evidence behind alerts.
 *
 * Distinct from the alert register: one alert can be backed by hundreds
 * of violations, and reviewing them is how a rule threshold gets tuned.
 */
export function ViolationsPage() {
  const table = useTableQuery<ViolationFilters>(INITIAL_FILTERS, {
    initialSortBy: 'occurred_at',
    initialPageSize: 25,
  });

  const query = useViolations({
    page: table.page,
    page_size: table.pageSize,
    sort_by: table.sort.sortBy,
    order: table.sort.order,
    search: table.search || undefined,
    ...table.filters,
  });

  const columns = useMemo<Column<Violation>[]>(
    () => [
      {
        key: 'severity',
        header: 'Severity',
        sortable: true,
        render: (row) => <LevelBadge level={row.severity} />,
      },
      {
        key: 'occurred_at',
        header: 'Observed',
        sortable: true,
        render: (row) => (
          <span title={formatDateTime(row.occurred_at)} className="whitespace-nowrap">
            {formatRelative(row.occurred_at)}
          </span>
        ),
      },
      {
        key: 'description',
        header: 'Description',
        className: 'w-full',
        render: (row) => (
          <span className="text-content-primary">{truncate(row.description, 80)}</span>
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
        key: 'track_id',
        header: 'Track',
        sortable: true,
        hideOnMobile: true,
        render: (row) => (
          <span className="font-mono">{row.track_id !== null ? `#${row.track_id}` : '—'}</span>
        ),
      },
      {
        key: 'frame',
        header: 'Frame',
        hideOnMobile: true,
        render: (row) => (
          <span className="font-mono tabular-nums">{row.frame_number ?? '—'}</span>
        ),
      },
      {
        key: 'alert_id',
        header: 'Alert',
        hideOnMobile: true,
        render: (row) =>
          row.alert_id ? (
            <span className="font-mono text-xs text-content-muted" title={row.alert_id}>
              {shortId(row.alert_id)}
            </span>
          ) : (
            <span className="text-content-muted">unlinked</span>
          ),
      },
    ],
    [],
  );

  return (
    <AppLayout
      title="Violations"
      subtitle="Per-frame rule breaches"
      onRefresh={() => void query.refetch()}
      isRefreshing={query.isFetching}
    >
      <Panel>
        <PanelHeader
          title="Violation Log"
          description={
            query.data
              ? `${query.data.meta.total} violation${query.data.meta.total === 1 ? '' : 's'} recorded`
              : 'Loading violations…'
          }
          icon={<ShieldAlert className="h-4 w-4" />}
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
              placeholder="Description or rule…"
            />
          </Field>
          <Field label="Severity">
            <Select
              value={table.filters.severity ?? ''}
              options={SEVERITY_OPTIONS}
              onValueChange={(value) => table.setFilter('severity', value)}
              placeholder="All severities"
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
          emptyTitle="No violations match these filters"
          emptyDescription="Violations are recorded per frame as rules evaluate the live feed."
        />
      </Panel>
    </AppLayout>
  );
}
