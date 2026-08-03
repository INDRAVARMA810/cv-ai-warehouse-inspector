# Deployment

Container deployment for the AI Warehouse Safety Inspector.

## Quick start

```bash
cp .env.example .env          # then edit POSTGRES_PASSWORD
docker compose up -d --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:8080 |
| API docs | http://localhost:8080/docs |
| Live stream | http://localhost:8080/api/v1/stream/live |

The first build downloads PyTorch, Ultralytics and OpenCV — expect
10–25 minutes depending on connection speed. Later builds are cached.

## Architecture

```
                    ┌──────────────────────────────┐
  host :8080  ─────►│ frontend  (nginx + React)    │
                    │  · serves the built bundle   │
                    │  · proxies /api → backend    │
                    └──────────────┬───────────────┘
                                   │  frontend_net
                    ┌──────────────▼───────────────┐
                    │ backend   (FastAPI + YOLO)   │
                    │  · REST API + MJPEG stream   │
                    │  · detection pipeline thread │
                    └──────────────┬───────────────┘
                                   │  backend_net
                    ┌──────────────▼───────────────┐
                    │ postgres  (16-alpine)        │
                    │  · volume: postgres_data     │
                    └──────────────────────────────┘
```

Two networks rather than one: the frontend has **no route to
PostgreSQL**. Only the backend sits on both.

The backend publishes no host port — the dashboard proxies everything,
so there is a single entry point to secure.

## Images

| Image | Base | Notes |
|---|---|---|
| `warehouse-safety/backend` | `python:3.12-slim-bookworm` | Two-stage; build toolchain discarded. Runs as UID 10001. |
| `warehouse-safety/frontend` | `nginx:1.27-alpine` | Two-stage; Node and `node_modules` never reach runtime. |
| `postgres:16-alpine` | official | Unmodified. |

### Backend build context

Built from the **repository root**, not `backend/`, because
`requirements.txt` lives at the root:

```bash
docker build -f backend/Dockerfile -t warehouse-backend .
```

The root `.dockerignore` excludes `venv/`, `frontend/`, `datasets/` and
model weights, keeping the context under ~1 MB.

`requirements.txt` is UTF‑16LE (written by `pip freeze` under
PowerShell), which pip on Linux cannot read. The Dockerfile normalises
it to UTF‑8 during the build, so the repository file is unchanged.

## GPU

The application selects its device at runtime via
`torch.cuda.is_available()`, so **the CPU image needs no change to run
on a GPU host** — it simply will not use the GPU. For actual
acceleration, build with CUDA wheels:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Requires the NVIDIA Container Toolkit. Adds roughly 2.5 GB to the image.

## Video source

`STREAM_SOURCE` is interpreted **inside the container**.

```bash
# Host footage — place files in ./videos, mounted read-only at /app/videos
STREAM_SOURCE=/app/videos/warehouse.mp4
```

A webcam (`STREAM_SOURCE=0`) needs the device passed through, which
works on Linux hosts only:

```yaml
services:
  backend:
    devices:
      - /dev/video0:/dev/video0
```

Docker Desktop on Windows and macOS cannot pass USB cameras into Linux
containers. Use a file or an RTSP URL there.

## Persistence

| Volume | Contents | Survives |
|---|---|---|
| `postgres_data` | Database | `down`, not `down -v` |
| `model_cache` | Ultralytics config and weights | Avoids re-downloading |
| `model_weights` | Custom weights | — |

```bash
docker compose down          # keeps data
docker compose down -v       # DELETES the database
```

Backup and restore:

```bash
docker compose exec postgres pg_dump -U postgres warehouse_ai > backup.sql
cat backup.sql | docker compose exec -T postgres psql -U postgres -d warehouse_ai
```

## Startup sequence

`depends_on` gates each stage on a healthcheck, so nothing starts
before what it needs is genuinely ready:

```
postgres healthy → backend starts → backend healthy → frontend starts
```

The backend entrypoint then, before uvicorn:

1. waits for the database to accept connections (`WAIT_FOR_DB`),
2. creates missing tables (`RUN_MIGRATIONS`),
3. optionally seeds demo data (`SEED_DEMO_DATA`).

This lives in the container layer, not application startup code, so the
app still runs outside Docker exactly as before.

> Schema **initialization** only creates missing tables — it never
> alters an existing one. Adopt Alembic before the schema evolves in
> production.

## Health

```bash
docker compose ps                      # STATUS column shows health
curl http://localhost:8080/api/v1/health
```

The backend healthcheck calls its own `/api/v1/health`, which returns
503 when the database is unreachable — so an unhealthy container really
does mean the service cannot serve requests.

## MJPEG through nginx

`multipart/x-mixed-replace` is an infinite response. With default
buffering nginx accumulates frames until its buffer fills, making the
feed stutter or appear frozen. The stream location therefore sets:

```nginx
proxy_buffering off;
proxy_read_timeout 24h;
```

Any additional proxy or load balancer in front needs the same treatment.

## Production checklist

- [ ] Set a real `POSTGRES_PASSWORD` in `.env` (never commit it)
- [ ] Terminate TLS in front of the frontend container
- [ ] **Add authentication** — every endpoint is currently unauthenticated
- [ ] Keep `POSTGRES_PORT` bound to `127.0.0.1`, or drop it entirely
- [ ] Set `SEED_DEMO_DATA=false`
- [ ] Configure log shipping; container logs are ephemeral
- [ ] Schedule `pg_dump` backups

## Troubleshooting

| Symptom | Cause |
|---|---|
| Backend unhealthy, restarting | Database unreachable — check `docker compose logs postgres` |
| Stream shows "Stream unavailable" | `STREAM_SOURCE` not resolvable inside the container |
| Feed frozen after a few frames | Proxy buffering enabled somewhere in front |
| Build fails on `requirements.txt` | Building from `backend/` instead of the repo root |
| Dashboard loads, API calls fail | `BACKEND_HOST`/`BACKEND_PORT` mismatch |

```bash
docker compose logs -f backend
docker compose exec backend python -c "from app.database import get_database; print(get_database().check_connection())"
```
