/**
 * Centralised React Query cache keys.
 *
 * Defining them in one place keeps invalidation predictable — a caller
 * cannot accidentally construct a key that almost matches an existing
 * one and silently duplicate a cache entry.
 */

import type {
  AlertQuery,
  AlertSearchBody,
  SystemEventQuery,
  TrackQuery,
  ViolationQuery,
} from '@/types';

export const queryKeys = {
  health: ['health'] as const,
  alerts: {
    all: ['alerts'] as const,
    list: (query: AlertQuery) => ['alerts', 'list', query] as const,
    search: (body: AlertSearchBody) => ['alerts', 'search', body] as const,
    detail: (alertId: string) => ['alerts', 'detail', alertId] as const,
  },
  violations: {
    all: ['violations'] as const,
    list: (query: ViolationQuery) => ['violations', 'list', query] as const,
  },
  tracks: {
    all: ['tracks'] as const,
    list: (query: TrackQuery) => ['tracks', 'list', query] as const,
  },
  systemEvents: {
    all: ['system-events'] as const,
    list: (query: SystemEventQuery) => ['system-events', 'list', query] as const,
  },
} as const;
