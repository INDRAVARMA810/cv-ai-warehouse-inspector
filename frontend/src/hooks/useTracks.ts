import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { fetchTracks } from '@/services';
import type { Paginated, Track, TrackQuery } from '@/types';
import { queryKeys } from './queryKeys';

/** Fetch a page of tracked-object lifetimes. */
export function useTracks(query: TrackQuery = {}): UseQueryResult<Paginated<Track>> {
  return useQuery({
    queryKey: queryKeys.tracks.list(query),
    queryFn: () => fetchTracks(query),
    placeholderData: (previous) => previous,
    staleTime: 5_000,
  });
}
