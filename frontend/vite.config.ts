import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

/**
 * Vite configuration.
 *
 * The dev server proxies `/api` to the FastAPI backend so the browser
 * sees a single origin. That keeps the backend free of CORS middleware
 * during development; a production deployment should either serve this
 * bundle from the same origin as the API or enable CORS explicitly.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendUrl = env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000';

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      rollupOptions: {
        output: {
          // Split the heavy, rarely-changing libraries out of the app
          // chunk so a code change does not invalidate the browser's
          // cached copy of React and the charting engine.
          manualChunks: {
            react: ['react', 'react-dom', 'react-router-dom'],
            charts: ['recharts'],
            data: ['@tanstack/react-query', 'axios'],
          },
        },
      },
    },
  };
});
