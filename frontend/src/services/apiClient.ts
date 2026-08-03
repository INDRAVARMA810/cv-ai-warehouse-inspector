/**
 * Configured Axios instance and error normalisation.
 *
 * This is the only module in the dashboard that knows about HTTP.
 * Everything above it works with typed resources and a single
 * `ApiError` shape, so a component never has to reason about status
 * codes or Axios internals.
 */

import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';
import type { ApiErrorBody } from '@/types';

// Optional chaining so the module can also be imported outside a Vite
// runtime (SSR smoke tests, unit tests), where `import.meta.env` is
// undefined rather than merely empty.
const BASE_URL = import.meta.env?.VITE_API_BASE_URL ?? '/api/v1';
const REQUEST_TIMEOUT_MS = 20_000;

/**
 * A normalised error the UI can render directly.
 *
 * `kind` distinguishes failures that call for different treatment:
 * a network drop and a 503 are both retryable and should say so, while
 * a 422 should surface field-level detail instead.
 */
export class ApiError extends Error {
  readonly status: number | null;
  readonly kind: 'network' | 'timeout' | 'client' | 'server' | 'unavailable' | 'unknown';
  readonly code: string;
  readonly fieldErrors: Array<{ field: string; message: string }>;

  constructor(
    message: string,
    options: {
      status?: number | null;
      kind?: ApiError['kind'];
      code?: string;
      fieldErrors?: Array<{ field: string; message: string }>;
    } = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = options.status ?? null;
    this.kind = options.kind ?? 'unknown';
    this.code = options.code ?? 'unknown_error';
    this.fieldErrors = options.fieldErrors ?? [];
  }

  /** Whether retrying the same request could plausibly succeed. */
  get isRetryable(): boolean {
    return this.kind === 'network' || this.kind === 'timeout' || this.kind === 'unavailable';
  }
}

/**
 * Convert any thrown value into an {@link ApiError}.
 *
 * The backend returns a consistent envelope (`{ error, detail, ... }`),
 * so its `detail` is preferred as the user-facing message; anything
 * else falls back to a generic message rather than leaking raw text.
 */
function normaliseError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorBody>;

    if (axiosError.code === 'ECONNABORTED') {
      return new ApiError('The request timed out. The server may be busy.', {
        kind: 'timeout',
        code: 'timeout',
      });
    }

    if (!axiosError.response) {
      return new ApiError('Cannot reach the safety platform API.', {
        kind: 'network',
        code: 'network_error',
      });
    }

    const { status, data } = axiosError.response;
    const detail = data?.detail ?? axiosError.message;

    const kind: ApiError['kind'] =
      status === 503 ? 'unavailable' : status >= 500 ? 'server' : 'client';

    return new ApiError(detail, {
      status,
      kind,
      code: data?.error ?? `http_${status}`,
      fieldErrors: (data?.errors ?? []).map((item) => ({
        field: item.field,
        message: item.message,
      })),
    });
  }

  return new ApiError(
    error instanceof Error ? error.message : 'An unexpected error occurred.',
  );
}

const client: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { Accept: 'application/json' },
});

client.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(normaliseError(error)),
);

/**
 * Strip empty values from a query object.
 *
 * Sending `?status=` would be rejected by the backend's enum
 * validation, so blank filters are removed rather than transmitted.
 */
export function cleanParams<T extends Record<string, unknown>>(params: T): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== undefined && value !== null && value !== '',
    ),
  );
}

/** Issue a GET request and return the parsed body. */
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const config: AxiosRequestConfig = params ? { params: cleanParams(params) } : {};
  const response = await client.get<T>(url, config);
  return response.data;
}

/** Issue a POST request and return the parsed body. */
export async function post<T>(url: string, body?: unknown): Promise<T> {
  const response = await client.post<T>(url, body);
  return response.data;
}

export default client;
