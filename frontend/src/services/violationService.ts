/** Violation resource access. */

import { get } from './apiClient';
import type { Paginated, Violation, ViolationQuery } from '@/types';

/** Fetch a filtered, paginated page of rule violations. */
export function fetchViolations(query: ViolationQuery = {}): Promise<Paginated<Violation>> {
  return get<Paginated<Violation>>('/violations', query as Record<string, unknown>);
}
