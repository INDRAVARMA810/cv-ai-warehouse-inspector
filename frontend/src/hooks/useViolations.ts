import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { fetchViolations } from '@/services';
import type { Paginated, Violation, ViolationQuery } from '@/types';
import { queryKeys } from './queryKeys';

/** Fetch a page of rule violations. */
export function useViolations(
  query: ViolationQuery = {},
): UseQueryResult<Paginated<Violation>> {
  return useQuery({
    queryKey: queryKeys.violations.list(query),
    queryFn: () => fetchViolations(query),
    placeholderData: (previous) => previous,
    staleTime: 5_000,
  });
}
