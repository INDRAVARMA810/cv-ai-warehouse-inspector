/** Live video stream access. */

import client, { get } from './apiClient';
import type { StreamStatus } from '@/types';

/** Fetch the current stream status. */
export function fetchStreamStatus(): Promise<StreamStatus> {
  return get<StreamStatus>('/stream/status');
}

/**
 * Build the URL for the MJPEG stream.
 *
 * The stream is consumed by an `<img>` element, not by Axios — the
 * browser decodes `multipart/x-mixed-replace` natively — so this
 * returns a URL rather than performing a request. It is resolved
 * against the same base URL as every other call so the dev proxy and a
 * deployed origin behave identically.
 *
 * @param fps Maximum frames per second requested.
 * @param nonce Cache-busting token. Changing it forces the browser to
 *   drop the old connection and open a new one, which is how
 *   reconnection is triggered.
 */
export function buildStreamUrl(fps = 15, nonce?: string | number): string {
  const base = client.defaults.baseURL ?? '/api/v1';
  const params = new URLSearchParams({ fps: String(fps) });
  if (nonce !== undefined) params.set('t', String(nonce));
  return `${base}/stream/live?${params.toString()}`;
}

/** Build the URL for a single-frame snapshot. */
export function buildSnapshotUrl(nonce?: string | number): string {
  const base = client.defaults.baseURL ?? '/api/v1';
  const query = nonce !== undefined ? `?t=${nonce}` : '';
  return `${base}/stream/snapshot${query}`;
}
