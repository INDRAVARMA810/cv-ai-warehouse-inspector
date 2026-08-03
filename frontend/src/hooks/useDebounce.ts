import { useEffect, useState } from 'react';

/**
 * Debounce a rapidly-changing value.
 *
 * Used for search inputs so a request is not issued on every keystroke.
 */
export function useDebounce<T>(value: T, delayMs = 350): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
