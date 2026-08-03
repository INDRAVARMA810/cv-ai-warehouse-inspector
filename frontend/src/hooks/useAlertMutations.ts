import { useMutation, useQueryClient, type UseMutationResult } from '@tanstack/react-query';
import { acknowledgeAlert, resolveAlert } from '@/services';
import type { Alert } from '@/types';
import { queryKeys } from './queryKeys';

/**
 * Acknowledge and resolve actions.
 *
 * Both invalidate every alert query on success rather than patching the
 * cache by hand: a status change moves an alert between filtered views
 * and shifts pagination, so a targeted update would leave other lists
 * stale in ways that are hard to reason about.
 */
export function useAcknowledgeAlert(): UseMutationResult<
  Alert,
  Error,
  { alertId: string; acknowledgedBy?: string }
> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ alertId, acknowledgedBy }) => acknowledgeAlert(alertId, acknowledgedBy),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.alerts.all });
    },
  });
}

export function useResolveAlert(): UseMutationResult<Alert, Error, { alertId: string }> {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ alertId }) => resolveAlert(alertId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.alerts.all });
    },
  });
}
