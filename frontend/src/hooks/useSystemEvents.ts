import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { fetchSystemEvents } from '@/services';
import type { Paginated, SystemEvent, SystemEventQuery } from '@/types';
import { queryKeys } from './queryKeys';

/** Fetch a page of operational system events. */
export function useSystemEvents(
  query: SystemEventQuery = {},
  refetchIntervalMs?: number,
): UseQueryResult<Paginated<SystemEvent>> {
  return useQuery({
    queryKey: queryKeys.systemEvents.list(query),
    queryFn: () => fetchSystemEvents(query),
    placeholderData: (previous) => previous,
    refetchInterval: refetchIntervalMs,
    staleTime: 5_000,
  });
}
