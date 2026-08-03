# syntax=docker/dockerfile:1.7

# =====================================================================
# AI Warehouse Safety Inspector — dashboard
#
# Multi-stage: Node compiles the bundle, then a minimal nginx image
# serves the static output and proxies the API. The Node toolchain and
# node_modules never reach the runtime image.
# =====================================================================

# ---------------------------------------------------------------------
# Stage 1 — build
# ---------------------------------------------------------------------
FROM node:22-alpine AS build

# Vite inlines environment variables at build time, so anything the
# bundle needs must be supplied here rather than at container start.
# The default is a relative path: requests then go to the same origin
# and are proxied by nginx, which means the built image needs no
# knowledge of where the backend lives.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app

# Copy manifests first so `npm ci` is cached until dependencies change.
COPY package.json package-lock.json* ./

# `npm ci` when a lockfile is present for reproducible installs, falling
# back to `npm install` when it is not.
RUN if [ -f package-lock.json ]; then \
        npm ci --no-audit --no-fund; \
    else \
        npm install --no-audit --no-fund; \
    fi

COPY . .

# Typecheck and bundle. `npm run build` runs `tsc -b && vite build`, so
# a type error fails the image build rather than shipping broken code.
RUN npm run build

# ---------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# Backend address the API proxy forwards to. Templated so a deployment
# can repoint it without rebuilding the bundle.
ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000

RUN rm -f /etc/nginx/conf.d/default.conf

# Rendered by nginx's own envsubst entrypoint at container start, which
# substitutes the BACKEND_* variables above.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=4s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
