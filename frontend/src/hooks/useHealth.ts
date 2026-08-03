import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { fetchHealth } from '@/services';
import type { Health } from '@/types';
import { queryKeys } from './queryKeys';

/** Poll platform health on a short interval so outages surface quickly. */
export function useHealth(refetchIntervalMs = 15_000): UseQueryResult<Health> {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: fetchHealth,
    refetchInterval: refetchIntervalMs,
    refetchOnWindowFocus: true,
    staleTime: 5_000,
  });
}
