/** Service health access. */

import client from './apiClient';
import type { Health } from '@/types';

/**
 * Fetch platform health.
 *
 * The endpoint deliberately answers with HTTP 503 when a dependency is
 * degraded, but the body still carries the per-component detail the
 * dashboard needs in order to show *what* is broken. `validateStatus`
 * therefore accepts 503 as a successful fetch; a genuine transport
 * failure still rejects and surfaces as an `ApiError`.
 */
export async function fetchHealth(): Promise<Health> {
  const response = await client.get<Health>('/health', {
    validateStatus: (status) => status === 200 || status === 503,
  });
  return response.data;
}
