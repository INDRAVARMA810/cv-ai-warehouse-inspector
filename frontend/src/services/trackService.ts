/** Tracked-object resource access. */

import { get } from './apiClient';
import type { Paginated, Track, TrackQuery } from '@/types';

/** Fetch a filtered, paginated page of tracked-object lifetimes. */
export function fetchTracks(query: TrackQuery = {}): Promise<Paginated<Track>> {
  return get<Paginated<Track>>('/tracks', query as Record<string, unknown>);
}
