import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { buildStreamUrl, fetchStreamStatus } from '@/services';
import type { StreamStatus } from '@/types';

/** Connection state of the MJPEG viewer. */
export type StreamConnectionState = 'connecting' | 'live' | 'reconnecting' | 'error';

interface UseMjpegStreamOptions {
  /** Maximum frames per second to request. */
  fps?: number;
  /** Give up after this many consecutive failures. */
  maxAttempts?: number;
  /**
   * Treat a connection that produces no first frame within this many
   * milliseconds as failed. Needed because a stalled MJPEG connection
   * never fires `error` — it simply hangs — so without a watchdog the
   * panel would spin forever.
   */
  firstFrameTimeoutMs?: number;
}

interface MjpegStream {
  /** Value to assign to an `<img>` `src`, or `undefined` while stopped. */
  src: string | undefined;
  state: StreamConnectionState;
  /** Consecutive failed attempts; resets on a successful frame. */
  attempt: number;
  /** Milliseconds until the next automatic retry, if one is scheduled. */
  retryInMs: number | null;
  /** Call from the `<img>` `onLoad` handler. */
  onLoad: () => void;
  /** Call from the `<img>` `onError` handler. */
  onError: () => void;
  /** Force an immediate reconnect, resetting the backoff. */
  reconnect: () => void;
}

/** Retry delays in milliseconds; the last value repeats. */
const BACKOFF_MS = [1000, 2000, 4000, 8000, 15000] as const;

/**
 * Manages an auto-reconnecting MJPEG connection.
 *
 * A browser renders `multipart/x-mixed-replace` natively in an `<img>`,
 * so the hook deliberately does not fetch or decode frames itself —
 * doing so in JavaScript would be far slower and would duplicate what
 * the image decoder already does well. Instead it owns the *connection
 * lifecycle*: when to (re)assign `src`, how long to wait before
 * retrying, and when to give up.
 *
 * Reconnection works by changing a nonce in the URL. Assigning the same
 * `src` string would be a no-op, so a cache-busting token is the only
 * reliable way to make the browser drop a dead connection and dial
 * again.
 */
export function useMjpegStream(options: UseMjpegStreamOptions = {}): MjpegStream {
  const { fps = 15, maxAttempts = 8, firstFrameTimeoutMs = 20_000 } = options;

  const [nonce, setNonce] = useState(() => Date.now());
  const [state, setState] = useState<StreamConnectionState>('connecting');
  const [attempt, setAttempt] = useState(0);
  const [retryInMs, setRetryInMs] = useState<number | null>(null);

  const retryTimer = useRef<number | null>(null);
  const watchdog = useRef<number | null>(null);
  const hasFrame = useRef(false);

  const clearTimers = useCallback(() => {
    if (retryTimer.current !== null) {
      window.clearTimeout(retryTimer.current);
      retryTimer.current = null;
    }
    if (watchdog.current !== null) {
      window.clearTimeout(watchdog.current);
      watchdog.current = null;
    }
  }, []);

  const scheduleRetry = useCallback(
    (nextAttempt: number) => {
      if (nextAttempt >= maxAttempts) {
        setState('error');
        setRetryInMs(null);
        return;
      }

      const delay = BACKOFF_MS[Math.min(nextAttempt, BACKOFF_MS.length - 1)];
      setState('reconnecting');
      setRetryInMs(delay);

      retryTimer.current = window.setTimeout(() => {
        hasFrame.current = false;
        setNonce(Date.now());
        setRetryInMs(null);
      }, delay);
    },
    [maxAttempts],
  );

  const handleFailure = useCallback(() => {
    clearTimers();
    setAttempt((current) => {
      const next = current + 1;
      scheduleRetry(next);
      return next;
    });
  }, [clearTimers, scheduleRetry]);

  const onLoad = useCallback(() => {
    // Fires on the first decoded frame. Later frames replace the image
    // in place without re-firing in most browsers, so this is treated
    // purely as "the connection produced something".
    hasFrame.current = true;
    clearTimers();
    setAttempt(0);
    setRetryInMs(null);
    setState('live');
  }, [clearTimers]);

  const onError = useCallback(() => {
    handleFailure();
  }, [handleFailure]);

  const reconnect = useCallback(() => {
    clearTimers();
    hasFrame.current = false;
    setAttempt(0);
    setRetryInMs(null);
    setState('connecting');
    setNonce(Date.now());
  }, [clearTimers]);

  // Watchdog: a connection that never delivers a first frame is dead
  // even though it never errored.
  useEffect(() => {
    if (state === 'error') return undefined;

    hasFrame.current = false;
    watchdog.current = window.setTimeout(() => {
      if (!hasFrame.current) handleFailure();
    }, firstFrameTimeoutMs);

    return () => {
      if (watchdog.current !== null) {
        window.clearTimeout(watchdog.current);
        watchdog.current = null;
      }
    };
  }, [nonce, firstFrameTimeoutMs, handleFailure, state]);

  // Close the connection when the component unmounts. Without this the
  // browser keeps the socket open and the server keeps encoding for a
  // viewer that is no longer on screen.
  useEffect(() => clearTimers, [clearTimers]);

  return {
    src: state === 'error' ? undefined : buildStreamUrl(fps, nonce),
    state,
    attempt,
    retryInMs,
    onLoad,
    onError,
    reconnect,
  };
}

/**
 * Poll stream status.
 *
 * Independent of the image connection: status tells the panel *why*
 * there is no picture (never started, camera failed, no frames yet),
 * which the `<img>` element alone cannot report.
 */
export function useStreamStatus(refetchIntervalMs = 10_000): UseQueryResult<StreamStatus> {
  return useQuery({
    queryKey: ['stream', 'status'],
    queryFn: fetchStreamStatus,
    refetchInterval: refetchIntervalMs,
    staleTime: 3_000,
    retry: 1,
  });
}
