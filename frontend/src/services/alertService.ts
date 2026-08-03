/** Alert resource access. Endpoints defined in `backend/app/api/routers/alerts.py`. */

import { get, post } from './apiClient';
import type { Alert, AlertQuery, AlertSearchBody, Paginated } from '@/types';

/** Fetch a filtered, paginated page of alerts. */
export function fetchAlerts(query: AlertQuery = {}): Promise<Paginated<Alert>> {
  return get<Paginated<Alert>>('/alerts', query as Record<string, unknown>);
}

/** Fetch a single alert by its public identifier. */
export function fetchAlert(alertId: string): Promise<Alert> {
  return get<Alert>(`/alerts/${encodeURIComponent(alertId)}`);
}

/**
 * Search alerts via the POST endpoint.
 *
 * Preferred over `fetchAlerts` when filtering by several levels at
 * once, which a query string cannot express cleanly.
 */
export function searchAlerts(body: AlertSearchBody = {}): Promise<Paginated<Alert>> {
  return post<Paginated<Alert>>('/alerts/search', body);
}

/** Mark an alert as seen by an operator. */
export function acknowledgeAlert(alertId: string, acknowledgedBy?: string): Promise<Alert> {
  return post<Alert>(`/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
    acknowledged_by: acknowledgedBy ?? null,
  });
}

/** Mark an alert's underlying hazard as cleared. */
export function resolveAlert(alertId: string): Promise<Alert> {
  return post<Alert>(`/alerts/${encodeURIComponent(alertId)}/resolve`);
}
