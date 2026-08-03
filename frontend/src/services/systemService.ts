/** System event resource access. */

import { get } from './apiClient';
import type { Paginated, SystemEvent, SystemEventQuery } from '@/types';

/** Fetch a filtered, paginated page of operational system events. */
export function fetchSystemEvents(
  query: SystemEventQuery = {},
): Promise<Paginated<SystemEvent>> {
  return get<Paginated<SystemEvent>>('/system/events', query as Record<string, unknown>);
}
