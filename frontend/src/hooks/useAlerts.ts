import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { fetchAlert, fetchAlerts, searchAlerts } from '@/services';
import type { Alert, AlertQuery, AlertSearchBody, Paginated } from '@/types';
import { queryKeys } from './queryKeys';

/**
 * Fetch a page of alerts.
 *
 * `placeholderData` keeps the previous page visible while the next one
 * loads, so paging and filtering do not flash an empty table.
 */
export function useAlerts(
  query: AlertQuery = {},
  refetchIntervalMs?: number,
): UseQueryResult<Paginated<Alert>> {
  return useQuery({
    queryKey: queryKeys.alerts.list(query),
    queryFn: () => fetchAlerts(query),
    placeholderData: (previous) => previous,
    refetchInterval: refetchIntervalMs,
    staleTime: 5_000,
  });
}

/** Search alerts via the POST endpoint, for multi-level filtering. */
export function useAlertSearch(
  body: AlertSearchBody,
  enabled = true,
): UseQueryResult<Paginated<Alert>> {
  return useQuery({
    queryKey: queryKeys.alerts.search(body),
    queryFn: () => searchAlerts(body),
    placeholderData: (previous) => previous,
    enabled,
    staleTime: 5_000,
  });
}

/** Fetch a single alert by public identifier. */
export function useAlert(alertId: string | null): UseQueryResult<Alert> {
  return useQuery({
    queryKey: queryKeys.alerts.detail(alertId ?? ''),
    queryFn: () => fetchAlert(alertId as string),
    enabled: Boolean(alertId),
  });
}
