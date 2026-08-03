/// <reference types="vite/client" />

/**
 * Typed environment variables.
 *
 * Declaring them explicitly means a typo in `import.meta.env.VITE_...`
 * is a compile error rather than a silent `undefined` at runtime.
 */
interface ImportMetaEnv {
  /** Base URL the dashboard calls, e.g. `/api/v1`. */
  readonly VITE_API_BASE_URL?: string;
  /** Backend origin the Vite dev proxy forwards to. */
  readonly VITE_BACKEND_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
