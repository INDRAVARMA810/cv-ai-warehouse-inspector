/**
 * TypeScript mirror of the backend's public API contract.
 *
 * These types correspond 1:1 to the Pydantic schemas in
 * `backend/app/api/schemas.py`. They are the single source of truth for
 * response shapes across the dashboard — nothing below `services/`
 * should re-declare them.
 */

export type AlertLevel = 'info' | 'low' | 'medium' | 'high' | 'critical';

export type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'expired';

export type AlertCategory =
  | 'zone_intrusion'
  | 'proximity'
  | 'occupancy'
  | 'ppe'
  | 'equipment'
  | 'system'
  | 'other';

export type SortOrder = 'asc' | 'desc';

/** Ordered least to most urgent; used for sorting and threshold checks. */
export const ALERT_LEVELS: readonly AlertLevel[] = [
  'info',
  'low',
  'medium',
  'high',
  'critical',
] as const;

export const ALERT_STATUSES: readonly AlertStatus[] = [
  'active',
  'acknowledged',
  'resolved',
  'expired',
] as const;

export const ALERT_CATEGORIES: readonly AlertCategory[] = [
  'zone_intrusion',
  'proximity',
  'occupancy',
  'ppe',
  'equipment',
  'system',
  'other',
] as const;

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Alert {
  id: number;
  alert_id: string;
  occurred_at: string;
  rule_name: string;
  level: AlertLevel;
  initial_level: AlertLevel | null;
  category: AlertCategory;
  status: AlertStatus;
  message: string;
  track_id: number | null;
  frame_number: number | null;
  bounding_box: BoundingBox | null;
  occurrence_count: number;
  first_seen: string | null;
  last_seen: string | null;
  acknowledged: boolean;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved: boolean;
  resolved_at: string | null;
  was_escalated: boolean;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface Violation {
  id: number;
  alert_id: string | null;
  occurred_at: string;
  rule_name: string;
  severity: AlertLevel;
  description: string;
  track_id: number | null;
  frame_number: number | null;
  bounding_box: BoundingBox | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface Track {
  id: number;
  track_id: number;
  class_id: number | null;
  class_name: string;
  confidence: number | null;
  first_seen: string;
  last_seen: string | null;
  first_frame: number | null;
  last_frame: number | null;
  observation_count: number;
  bounding_box: BoundingBox | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface SystemEvent {
  id: number;
  occurred_at: string;
  event_type: string;
  level: string;
  source: string | null;
  message: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface PageMeta {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface Paginated<T> {
  items: T[];
  meta: PageMeta;
}

export interface ComponentHealth {
  name: string;
  healthy: boolean;
  detail: string | null;
}

export interface Health {
  status: 'ok' | 'degraded';
  application: string;
  version: string;
  components: ComponentHealth[];
}

/** The backend's standard error envelope. */
export interface ApiErrorBody {
  error: string;
  detail: string;
  status_code: number;
  path: string | null;
  errors: Array<{ field: string; message: string; type: string }> | null;
}

/* ------------------------------------------------------------------ */
/* Query parameter shapes                                              */
/* ------------------------------------------------------------------ */

export interface PaginationQuery {
  page?: number;
  page_size?: number;
}

export interface SortQuery {
  sort_by?: string;
  order?: SortOrder;
}

export interface TimeRangeQuery {
  since?: string;
  until?: string;
}

export interface AlertQuery extends PaginationQuery, SortQuery, TimeRangeQuery {
  status?: AlertStatus;
  level?: AlertLevel;
  category?: AlertCategory;
  rule_name?: string;
  track_id?: number;
  acknowledged?: boolean;
  resolved?: boolean;
  search?: string;
}

/** Body accepted by `POST /alerts/search`; supports multi-level filtering. */
export interface AlertSearchBody extends PaginationQuery, TimeRangeQuery {
  status?: AlertStatus;
  level?: AlertLevel;
  levels?: AlertLevel[];
  category?: AlertCategory;
  rule_name?: string;
  track_id?: number;
  acknowledged?: boolean;
  resolved?: boolean;
  search?: string;
  sort_by?: string;
  order?: SortOrder;
}

export interface ViolationQuery extends PaginationQuery, SortQuery, TimeRangeQuery {
  rule_name?: string;
  severity?: AlertLevel;
  track_id?: number;
  alert_id?: string;
  search?: string;
}

export interface TrackQuery extends PaginationQuery, SortQuery, TimeRangeQuery {
  track_id?: number;
  class_name?: string;
  min_observations?: number;
  search?: string;
}

export interface SystemEventQuery extends PaginationQuery, SortQuery, TimeRangeQuery {
  event_type?: string;
  level?: string;
  source?: string;
  search?: string;
}

/** Live video stream status, from `GET /stream/status`. */
export interface StreamStatus {
  available: boolean;
  running: boolean;
  auto_start: boolean;
  viewers: number;
  frames_published: number;
  frames_encoded: number;
  publish_fps: number;
  last_frame_age: number | null;
  frame_width: number | null;
  frame_height: number | null;
  jpeg_quality: number;
  device: string | null;
  source: string;
  uptime: number | null;
  error: string | null;
}
