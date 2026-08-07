<div align="center">

# 🦺 AI Warehouse Safety Inspector

**Real-time computer-vision safety monitoring for industrial warehouse floors.**

Detects people and equipment from a live camera feed, tracks them across frames, evaluates
configurable safety rules against spatial zones, and raises deduplicated alerts to an
industrial control-room dashboard — end to end, on GPU or CPU.

<br />

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?style=flat-square)](https://docs.ultralytics.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Demo](#-demo)
- [Screenshots](#-screenshots)
- [Features](#-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Installation](#-installation)
  - [Docker (recommended)](#docker-recommended)
  - [Local development](#local-development)
- [Environment Variables](#-environment-variables)
- [Folder Structure](#-folder-structure)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Performance](#-performance)
- [Known Limitations](#-known-limitations)
- [Future Improvements](#-future-improvements)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

Industrial warehouses carry persistent, well-understood hazards: pedestrians straying into
machinery envelopes, forklifts passing too close to people on foot, and zones exceeding safe
occupancy. Human observation does not scale across shifts and cameras.

This project applies a full computer-vision pipeline to that problem and treats the result
as **operations software**, not a demo notebook. Every stage is a separately testable module
with an explicit contract:

```
Camera ─▶ Preprocess ─▶ YOLOv8 ─▶ ByteTrack ─▶ Rule Engine ─▶ Alert Engine ─▶ PostgreSQL
                                       │                                          │
                                       └────────▶ MJPEG Stream ──▶ React Dashboard ◀┘
```

The design decision that shapes the whole system is **deduplication**. A person standing in a
danger zone for ten seconds produces ~300 rule violations at 30 fps. Forwarding those to an
operator would be unusable. The alert engine collapses them into **one durable incident** with
an occurrence counter, escalation history and lifecycle — measured at a **300× reduction** in
this repository's own verification run.

---

## 🎬 Demo

> **📹 Demo GIF placeholder** — record a short capture of the dashboard with a live feed and
> place it at `screenshots/demo.gif`, then the embed below will render.

<div align="center">

<!-- ![AI Warehouse Safety Inspector — live demo](screenshots/demo.gif) -->

`screenshots/demo.gif` — *not yet recorded*

</div>

**Suggested capture sequence:** dashboard with live feed → a person entering a danger zone →
the critical alert appearing in the register → acknowledging it from the detail drawer.

---

## 📸 Screenshots

> **Placeholders.** The `screenshots/` directory is present but empty. Capture each view at
> **1680×1150** or wider (dark mode only) and drop the files in with the names below.

| View | File | Description |
|:--|:--|:--|
| 🖥️ **Dashboard** | `screenshots/dashboard.png` | Live feed, KPI cluster, charts, recent-alert register |
| 📹 **Live Monitoring** | `screenshots/live-monitoring.png` | Full-bleed annotated feed with side rail |
| 🚨 **Alerts** | `screenshots/alerts.png` | Filterable register + acknowledge/resolve drawer |
| ⚠️ **Violations** | `screenshots/violations.png` | Per-frame rule-breach log |
| 🎯 **Tracks** | `screenshots/tracks.png` | Tracked-object lifetimes and dwell times |
| 📊 **Analytics** | `screenshots/analytics.png` | Alerts by hour, severity mix, zone breakdown |
| 💚 **System Health** | `screenshots/system-health.png` | Subsystem board and event log |

<div align="center">

<!-- ![Dashboard](screenshots/dashboard.png) -->

</div>

---

## ✨ Features

### 🧠 Computer Vision Pipeline

- **YOLOv8 object detection** via Ultralytics, with a thread-safe model cache keyed by
  `weights:device` so repeated loads are free.
- **Automatic device selection** — CUDA when available, CPU fallback otherwise, with no
  configuration change required.
- **ByteTrack multi-object tracking** assigning stable identities across frames, with rolling
  per-identity history for dwell analysis.
- **Chainable image preprocessing** — resize, CLAHE, histogram equalisation, colour-space
  conversion, blur, brightness/contrast.
- **Defensive imports** throughout: the API imports and runs on machines with no GPU, no
  camera, and no Torch installed.

### 🛡️ Safety Rule Engine

Rules are pure functions of a frame context — no I/O, no drawing, no persistence — so each is
independently testable and the engine can run them in any order.

| Rule | What it detects |
|:--|:--|
| `RestrictedZoneRule` | Monitored classes entering **danger** or **restricted** zones (danger escalates to `CRITICAL`) |
| `MinimumDistanceRule` | Person↔forklift pairs closer than a pixel threshold; each pair reported once |
| `MaximumWorkersRule` | Occupancy limits, frame-wide or scoped to a single zone |
| `PPEPlaceholderRule` | ⚠️ Registered but **disabled** — see [Known Limitations](#-known-limitations) |

- **Zone geometry** — axis-aligned rectangles and arbitrary polygons, with `contains_point`
  (ray casting), `intersects_box` (all three overlap cases) and `distance_to`.
- **Failure isolation** — a rule that raises is logged, recorded in `failed_rules`, and the
  remaining rules still run. One bad rule can never blank an entire evaluation.

### 🔔 Alert Management

- **Grouping** by incident identity (rule + track + zone).
- **Deduplication** — an ongoing hazard updates its existing alert instead of raising a new one.
- **Cooldown** — a re-raise after an incident closes is suppressed until a timeout elapses,
  preventing flapping.
- **Gradual escalation** — a persisting incident climbs one severity level per threshold
  interval, never one per frame.
- **Lifecycle** — `active → acknowledged → resolved | expired`, with terminal states that
  cannot be reopened, preserving the audit trail.
- **Notification policy** — routing decisions for Dashboard / Email / SMS / Audio / Webhook.
  ⚠️ Decisions only; no delivery code exists.

### 🎥 Live MJPEG Streaming

- **`multipart/x-mixed-replace`** rendered natively by any browser in a plain `<img>` — no
  client-side video decoding.
- **Latest-frame-wins hand-off** — a slow viewer can never apply back-pressure to the
  inference loop.
- **Encode-once caching** — a frame is JPEG-encoded once per sequence number regardless of
  viewer count.
- **Auto-reconnect** in the dashboard with exponential backoff and a stalled-connection
  watchdog.

### 📊 Industrial Dashboard

- **Dark-mode control-room aesthetic** — neutral graphite surfaces so emerald/amber/red status
  colour is the only saturated element on screen.
- **8 routes** — Dashboard, Live Monitoring, Alerts, Violations, Tracks, Analytics, System
  Health, Settings.
- **6 charts** — alerts by hour, severity distribution, zone-wise violations, occupancy trend,
  average dwell time, top rules.
- **Complete state coverage** — every widget implements loading (directional sweep skeletons),
  empty (with a *positive* variant, because zero alerts is good news), error (copy adapts to
  network vs. outage vs. timeout) and live states.
- **Server-driven pagination, filtering, sorting and search** on every table.

### 🗄️ Persistence

- **Repository pattern** — every read and write goes through a repository; no business logic
  builds a query.
- **Live persistence** — `LivePersistence` writes deduplicated alerts and upserted tracks from
  the running pipeline, debounced so a session opens only for frames with something new.
- **Four tables** — `alert_records`, `violation_records`, `track_records`, `system_events`.
- **Dialect-portable** — `JSONB` on PostgreSQL, generic `JSON` elsewhere.

---

## 🏗️ Architecture

### Layered design

```
┌──────────────────────────────────────────────────────────────────────┐
│  PRESENTATION            React 18 · TypeScript · Tailwind · Recharts │
│  pages → components → hooks → services → types                       │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │  HTTP / MJPEG
┌────────────────────────────────▼─────────────────────────────────────┐
│  API                     FastAPI · Pydantic v2 · OpenAPI             │
│  routers → dependencies → schemas → exception handlers               │
│  ⚠ no router imports SQLAlchemy or builds a query                    │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│  DOMAIN                                                              │
│                                                                      │
│   video ──▶ image_processing ──▶ detection ──▶ tracking              │
│                                                     │                │
│                                                     ▼                │
│                                    rules ──▶ alerts                  │
│                                                     │                │
│                                    streaming ◀──────┘                │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │  repositories only
┌────────────────────────────────▼─────────────────────────────────────┐
│  PERSISTENCE             SQLAlchemy 2.0 · psycopg 3 · PostgreSQL 16  │
│  database → session → models → repositories → migrations → seed      │
└──────────────────────────────────────────────────────────────────────┘
```

### Runtime topology (Docker)

```
                    ┌──────────────────────────────┐
  host :8080  ─────▶│  frontend   nginx + React    │
                    │   · serves the built bundle  │
                    │   · proxies /api → backend   │
                    └──────────────┬───────────────┘
                                   │  frontend_net
                    ┌──────────────▼───────────────┐
                    │  backend    FastAPI + YOLO   │
                    │   · REST API + MJPEG stream  │
                    │   · pipeline worker thread   │
                    └──────────────┬───────────────┘
                                   │  backend_net
                    ┌──────────────▼───────────────┐
                    │  postgres   16-alpine        │
                    │   · volume: postgres_data    │
                    └──────────────────────────────┘
```

**Two networks, not one.** The frontend has *no route* to PostgreSQL — only the backend sits on
both. The backend publishes no host port, so there is a single entry point to secure.

### Key design decisions

| Decision | Rationale |
|:--|:--|
| **Layer decoupling by duck typing** | `tracking` doesn't import `detection`; `rules` doesn't import `tracking`. Layers match on structure, so any one can be swapped without touching its neighbours. |
| **Repositories own all SQL** | Business logic never builds a query. Verified by inspection: no router imports SQLAlchemy. |
| **Producer never blocks** | `StreamManager.publish()` never queues. Encoding happens outside the producer's lock, so viewers can never delay inference. |
| **Lazy heavy imports** | Torch/OpenCV/Ultralytics load only when a stream starts, keeping API import cheap and portable. |
| **Sort allowlists** | Sorting is resolved against a per-repository allowlist, so an arbitrary column name never reaches the query builder. |
| **Status colour is reserved** | Nothing decorative is emerald/amber/red — when an operator sees one, it always means something. |

---

## 🛠️ Technology Stack

### Backend

| Component | Version | Purpose |
|:--|:--|:--|
| Python | 3.12 | Runtime |
| FastAPI | 0.141.1 | REST API framework |
| Pydantic | 2.13.4 | Schema validation, OpenAPI generation |
| SQLAlchemy | 2.0.51 | ORM (typed 2.0 style) |
| psycopg | 3.3.4 | PostgreSQL driver |
| PostgreSQL | 16-alpine | Primary datastore |
| Ultralytics | 8.4.115 | YOLOv8 detection + ByteTrack |
| PyTorch | 2.13.0 | Inference backend (CUDA or CPU) |
| OpenCV | 5.0.0 | Capture, preprocessing, JPEG encoding |
| Uvicorn | 0.52.0 | ASGI server |
| Loguru | 0.7.3 | Structured logging |

### Frontend

| Component | Version | Purpose |
|:--|:--|:--|
| React | 18.3 | UI framework |
| TypeScript | 5.6 | Type safety |
| Vite | 5.4 | Build tool + dev proxy |
| Tailwind CSS | 3.4 | Design-token styling |
| TanStack Query | 5.59 | Server-state caching and polling |
| Axios | 1.7 | HTTP client + error normalisation |
| React Router | 6.27 | Routing |
| Recharts | 2.13 | Charting |
| Lucide React | 0.454 | Icons |
| Inter / JetBrains Mono | 5.3 | Self-hosted typefaces |

### Infrastructure

Docker · Docker Compose · nginx 1.27-alpine · NVIDIA Container Toolkit *(optional, for GPU)*

---

## 🚀 Installation

### Docker (recommended)

**Prerequisites:** Docker Engine 24+ and Docker Compose v2+.

```bash
git clone <repository-url>
cd AI-Warehouse-Safety-Inspector

cp .env.example .env
#  ⚠️ edit .env and set a real POSTGRES_PASSWORD

docker compose up -d --build
```

| Service | URL |
|:--|:--|
| 🖥️ Dashboard | http://localhost:8080 |
| 📚 API docs (Swagger) | http://localhost:8080/docs |
| 📕 API docs (ReDoc) | http://localhost:8080/redoc |
| 🎥 Live stream | http://localhost:8080/api/v1/stream/live |

> ⏱️ **First build takes 10–25 minutes** — PyTorch, Ultralytics and OpenCV are large
> downloads. Subsequent builds are cached.

**Start with demo data and sample footage:**

```bash
# in .env
SEED_DEMO_DATA=true
STREAM_SOURCE=/app/videos/warehouse-demo.mp4   # place footage in ./videos
```

**GPU acceleration** *(requires NVIDIA Container Toolkit)*:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Verify a running deployment:

```bash
node scripts/verify-deployment.mjs http://localhost:8080
```

---

### Local development

**Prerequisites:** Python 3.12, Node.js 20+, and PostgreSQL 16 *(or use SQLite for a quick start)*.

#### 1️⃣ Backend

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install "lap>=0.5.12"         # ByteTrack's linear-assignment solver

cd backend
cp .env.example .env              # set DATABASE_URL
```

> 💡 `requirements.txt` is UTF-16LE (produced by `pip freeze` under PowerShell). Linux/macOS
> may need `iconv -f UTF-16 -t UTF-8 requirements.txt -o requirements-utf8.txt` first.
> The Docker build handles this automatically.

Initialise the schema and start the API:

```bash
python -c "from app.database import initialize; initialize()"
python -m app.database.seed          # optional demo data

uvicorn app.main:app --reload --port 8000
```

#### 2️⃣ Frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

> ⚠️ Vite binds to `localhost` (IPv6). Use `http://localhost:5173`, **not** `127.0.0.1`.
> If port 5173 is taken, Vite silently moves to 5174 — check the console output.

#### 3️⃣ Standalone pipeline *(no API)*

```bash
cd backend
python run_camera.py                             # camera feed only
python run_detection.py                          # full pipeline, OpenCV window
python run_detection.py --source video.mp4 --device cpu
```

> ⚠️ `run_detection.py` runs in **its own process**. `StreamManager` is a process-wide
> singleton, so those frames are **not** visible to the API. For the dashboard stream, the
> pipeline must run inside the API process — which it does automatically.

---

## ⚙️ Environment Variables

### 🗄️ Database

| Variable | Default | Description |
|:--|:--|:--|
| `DATABASE_URL` | `postgresql://postgres:password@localhost:5432/warehouse_ai` | Connection string. A bare `postgresql://` scheme is auto-rewritten to `postgresql+psycopg://`. |
| `DB_POOL_SIZE` | `5` | Connections held in the pool |
| `DB_MAX_OVERFLOW` | `10` | Extra connections allowed during bursts |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait for a free connection |
| `DB_POOL_RECYCLE` | `1800` | Seconds before a connection is recycled |
| `DB_POOL_PRE_PING` | `true` | Validate a connection before handing it out |
| `DB_ECHO` | `false` | Log every SQL statement |

### 🎥 Video Stream

| Variable | Default | Description |
|:--|:--|:--|
| `STREAM_SOURCE` | `0` | Webcam index or video path **inside the container** |
| `STREAM_WEIGHTS` | `yolov8n.pt` | YOLO weights path or built-in model name |
| `STREAM_DEVICE` | *(auto)* | `cuda` / `cpu`; blank auto-selects |
| `STREAM_CONF` | `0.25` | Detection confidence threshold |
| `STREAM_IOU` | `0.45` | NMS IoU threshold |
| `STREAM_WIDTH` | `960` | Inference frame width |
| `STREAM_HEIGHT` | `540` | Inference frame height |
| `STREAM_FPS` | `30` | Expected source rate (sizes tracker buffer) |
| `STREAM_LOOP` | `true` | Restart video files when they end |
| `STREAM_AUTO_START` | `true` | Start capture on the first viewer |
| `STREAM_IDLE_STOP` | `60` | Release the camera after N idle seconds (`0` = never) |
| `CAMERA_BACKEND` | `auto` | OpenCV capture backend for webcam sources |

### 🐳 Container Startup

| Variable | Default | Description |
|:--|:--|:--|
| `WAIT_FOR_DB` | `90` | Seconds to wait for the database before giving up |
| `RUN_MIGRATIONS` | `true` | Create missing tables on start |
| `SEED_DEMO_DATA` | `false` | Insert demo rows into an empty database |

### 🌐 Application & Frontend

| Variable | Default | Description |
|:--|:--|:--|
| `APP_NAME` | `AI Warehouse Safety Inspector` | Displayed application name |
| `APP_VERSION` | `1.0.0` | Displayed version |
| `LOG_LEVEL` | `INFO` | Minimum log severity |
| `FRONTEND_PORT` | `8080` | Host port for the dashboard |
| `VITE_API_BASE_URL` | `/api/v1` | API base — relative so nginx proxies it |
| `VITE_BACKEND_URL` | `http://127.0.0.1:8000` | Dev-proxy target |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres` / `password` / `warehouse_ai` | Database credentials |
| `POSTGRES_PORT` | `127.0.0.1:5432` | Host binding — loopback by default |
| `TORCH_INDEX_URL` | *(CPU wheels)* | Set to a CUDA index for a GPU image |

---

## 📁 Folder Structure

```
AI-Warehouse-Safety-Inspector/
│
├── backend/
│   ├── app/
│   │   ├── video/                  🎥 Capture layer
│   │   │   ├── camera.py               OpenCV wrapper, context manager, safe release
│   │   │   ├── video_reader.py         Frame resize / colour conversion
│   │   │   └── fps.py                  Rolling FPS counter + overlay
│   │   │
│   │   ├── image_processing/       🖼️ Preprocessing
│   │   │   ├── preprocessor.py         Chainable ops (CLAHE, resize, normalise…)
│   │   │   ├── image_utils.py          Stateless load/save/crop/pad helpers
│   │   │   └── augmentations.py        Training-time augmentations
│   │   │
│   │   ├── detection/              🎯 YOLOv8 inference
│   │   │   ├── model_loader.py         Thread-safe cache, device resolution
│   │   │   ├── yolo_engine.py          Ultralytics wrapper, result parsing
│   │   │   ├── detector.py             High-level API, graceful degradation
│   │   │   └── detection_result.py     BoundingBox / Detection / DetectionResult
│   │   │
│   │   ├── tracking/               🔄 Multi-object tracking
│   │   │   ├── bytetrack_engine.py     ByteTrack wrapper + detection adapter
│   │   │   ├── tracker.py              Orchestration, per-identity history
│   │   │   ├── tracked_object.py       TrackedObject / TrackHistory / TrackState
│   │   │   └── tracker_utils.py        Coordinate conversions, validation
│   │   │
│   │   ├── rules/                  🛡️ Safety rule engine
│   │   │   ├── rule.py                 BaseRule contract + RuleContext
│   │   │   ├── safety_rules.py         Zone / distance / occupancy / PPE rules
│   │   │   ├── zone.py                 Rectangle + polygon geometry
│   │   │   ├── rule_registry.py        Registration, enable/disable, priority
│   │   │   ├── rule_engine.py          Evaluation with failure isolation
│   │   │   └── rule_result.py          Severity / RuleViolation / RuleResult
│   │   │
│   │   ├── alerts/                 🔔 Alert management
│   │   │   ├── alert.py                Alert / AlertLevel / AlertStatus / Category
│   │   │   ├── alert_engine.py         Grouping, dedup, cooldown, escalation
│   │   │   ├── alert_manager.py        Lifecycle ownership + querying
│   │   │   ├── alert_history.py        Rolling buffer, search, export, stats
│   │   │   ├── cooldown.py             Reusable rate-limiting primitive
│   │   │   └── notification_policy.py  Routing decisions only — no delivery
│   │   │
│   │   ├── database/               🗄️ Persistence
│   │   │   ├── database.py             Engine, pooling, lazy connection
│   │   │   ├── session.py              Scoped sessions, transaction scope
│   │   │   ├── models.py               4 ORM tables, JSONB-portable
│   │   │   ├── repositories.py         ⭐ The only module that touches SQL
│   │   │   ├── migrations.py           Schema initialisation
│   │   │   └── seed.py                 Idempotent demo data
│   │   │
│   │   ├── streaming/              📡 MJPEG streaming
│   │   │   ├── frame_encoder.py        JPEG encoding, quality, downscale
│   │   │   ├── stream_manager.py       Thread-safe latest-frame hand-off
│   │   │   ├── stream.py               Pipeline worker thread
│   │   │   ├── mjpeg.py                multipart/x-mixed-replace generator
│   │   │   └── persistence.py          Writes live output to the database
│   │   │
│   │   ├── api/                    🌐 REST layer
│   │   │   ├── routers/                One module per resource
│   │   │   ├── schemas.py              Pydantic v2 request/response contract
│   │   │   ├── dependencies.py         Session + repository injection
│   │   │   └── exceptions.py           Global handlers, single error envelope
│   │   │
│   │   ├── config.py               Settings from .env
│   │   ├── logger.py               Loguru sinks with rotation
│   │   └── main.py                 FastAPI entry point
│   │
│   ├── run_camera.py               Standalone camera preview
│   ├── run_detection.py            Standalone end-to-end pipeline
│   ├── Dockerfile                  Multi-stage, non-root, tini
│   └── docker-entrypoint.sh        Wait-for-DB → migrate → seed → serve
│
├── frontend/
│   └── src/
│       ├── types/                  📘 API contract mirror (source of truth)
│       ├── services/               🔌 The only modules that speak HTTP
│       ├── hooks/                  🪝 React Query wrappers + table state
│       ├── utils/                  🧰 Formatting, severity tones, statistics
│       ├── components/
│       │   ├── ui/                     Panel, StatCard, DataTable, Badge…
│       │   ├── layout/                 AppLayout, Sidebar, TopBar
│       │   ├── charts/                 Recharts wrappers + shared theme
│       │   ├── alerts/                 Feed + detail drawer
│       │   └── dashboard/              Camera, system status, activity feed
│       └── pages/                  📄 8 routes
│
├── docker/postgres/init/           SQL run once on first DB init
├── docs/DEPLOYMENT.md              Full deployment guide
├── scripts/verify-deployment.mjs   Post-deploy verification suite
├── videos/                         Host footage (mounted read-only)
├── docker-compose.yml              Full stack
├── docker-compose.gpu.yml          GPU overlay
└── requirements.txt                Python dependencies
```

---

## 📡 API Documentation

Interactive documentation is generated from the code and served at **`/docs`** (Swagger UI),
**`/redoc`** (ReDoc) and **`/openapi.json`**.

All endpoints are versioned under **`/api/v1`**.

### Endpoints

| Method | Endpoint | Description |
|:--|:--|:--|
| `GET` | `/health` | Service and per-component health. Returns **503** when degraded. |
| `GET` | `/alerts` | List alerts — paginated, filtered, sorted, searchable |
| `GET` | `/alerts/{alert_id}` | Fetch one alert by public UUID |
| `POST` | `/alerts/search` | Search with a body — supports multi-level filtering |
| `POST` | `/alerts/{alert_id}/acknowledge` | Mark as seen by an operator |
| `POST` | `/alerts/{alert_id}/resolve` | Mark the hazard as cleared |
| `GET` | `/violations` | List per-frame rule violations |
| `GET` | `/tracks` | List tracked-object lifetimes |
| `GET` | `/system/events` | List operational system events |
| `GET` | `/stream/live` | **MJPEG** live annotated feed |
| `GET` | `/stream/snapshot` | Single JPEG frame |
| `GET` | `/stream/status` | Stream throughput, viewers, device |

### Common query parameters

| Parameter | Applies to | Description |
|:--|:--|:--|
| `page`, `page_size` | all lists | Pagination — `page_size` capped at **500** |
| `sort_by`, `order` | all lists | Sorting; unsupported keys fall back to the default ordering |
| `since`, `until` | all lists | ISO-8601 time bounds |
| `search` | all lists | Case-insensitive substring across text fields |
| `status`, `level`, `category`, `rule_name`, `track_id`, `acknowledged`, `resolved` | `/alerts` | Resource filters |
| `severity`, `alert_id` | `/violations` | Resource filters |
| `class_name`, `min_observations` | `/tracks` | Resource filters |
| `event_type`, `level`, `source` | `/system/events` | Resource filters |

### Response shape

Every list endpoint returns the same envelope:

```json
{
  "items": [ ... ],
  "meta": {
    "total": 128, "page": 1, "page_size": 25,
    "pages": 6, "has_next": true, "has_previous": false
  }
}
```

### Error envelope

A single predictable shape for every failure, so clients need one parsing path:

```json
{
  "error": "validation_error",
  "detail": "Request validation failed.",
  "status_code": 422,
  "path": "/api/v1/alerts",
  "errors": [
    { "field": "query.page", "message": "Input should be greater than or equal to 1", "type": "greater_than_equal" }
  ]
}
```

| Status | Meaning |
|:--|:--|
| `404` | Resource not found |
| `422` | Validation failed — `errors[]` carries field-level detail |
| `503` | Database unavailable — retryable; no internal detail is leaked |
| `500` | Unhandled fault — logged in full server-side, generic to the client |

### Examples

```bash
# Critical, unresolved alerts
curl "http://localhost:8080/api/v1/alerts?level=critical&resolved=false&page_size=10"

# Multi-level search
curl -X POST http://localhost:8080/api/v1/alerts/search \
  -H "Content-Type: application/json" \
  -d '{"levels":["critical","high"],"page_size":25,"order":"desc"}'

# Acknowledge an incident
curl -X POST http://localhost:8080/api/v1/alerts/<uuid>/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"acknowledged_by":"supervisor.chen"}'

# Long-lived tracks
curl "http://localhost:8080/api/v1/tracks?min_observations=100&sort_by=observation_count&order=desc"
```

---

## 🚢 Deployment

Full guide: **[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)**

### Startup ordering

`depends_on` gates each stage on a healthcheck, so nothing starts before what it needs is ready:

```
postgres healthy ──▶ backend starts ──▶ backend healthy ──▶ frontend starts
```

The backend entrypoint then, before Uvicorn: waits for the database → creates missing tables →
optionally seeds demo data. This lives in the **container layer**, not application startup, so
the app still runs outside Docker unchanged.

### Images

| Image | Base | Size | Notes |
|:--|:--|:--|:--|
| `warehouse-safety/backend` | `python:3.12-slim-bookworm` | **1.89 GB** | Two-stage; build toolchain discarded; runs as UID 10001 |
| `warehouse-safety/frontend` | `nginx:1.27-alpine` | **52.3 MB** | Two-stage; Node never reaches runtime |

> The backend image builds from the **repository root**, not `backend/`, because
> `requirements.txt` lives at the root. The root `.dockerignore` keeps the context under ~1 MB.

### Persistence

| Volume | Contents | Survives |
|:--|:--|:--|
| `postgres_data` | Database | `down` ✅ · `down -v` ❌ |
| `model_cache` | Ultralytics config and weights | Avoids re-downloading |
| `model_weights` | Custom weights | — |

```bash
docker compose down      # keeps data
docker compose down -v   # ⚠️ DELETES the database

# Backup / restore
docker compose exec postgres pg_dump -U postgres warehouse_ai > backup.sql
cat backup.sql | docker compose exec -T postgres psql -U postgres -d warehouse_ai
```

### MJPEG through a proxy

`multipart/x-mixed-replace` is an infinite response. With default buffering, nginx accumulates
frames until its buffer fills, making the feed stutter or appear frozen. The stream location
therefore sets:

```nginx
proxy_buffering off;
proxy_read_timeout 24h;
```

**Any additional proxy or load balancer in front needs the same treatment.**

### Production checklist

- [ ] Set a real `POSTGRES_PASSWORD` (never commit `.env`)
- [ ] Terminate TLS in front of the frontend container
- [ ] 🔴 **Add authentication** — every endpoint is currently open
- [ ] Keep `POSTGRES_PORT` bound to `127.0.0.1`, or remove it entirely
- [ ] Set `SEED_DEMO_DATA=false`
- [ ] Configure log shipping — container logs are ephemeral
- [ ] Schedule `pg_dump` backups
- [ ] Adopt Alembic before the schema evolves

---

## ⚡ Performance

> Measured in this repository's own verification runs. **Hardware:** NVIDIA GeForce RTX 4050
> Laptop GPU, 12 vCPU, 8 GB container memory. Figures will vary with hardware, model size and
> resolution.

### Inference

| Metric | Value | Conditions |
|:--|:--:|:--|
| Live throughput | **24–26 fps** | YOLOv8n · 640×360 · CUDA |
| Rule evaluation | **0.02–0.21 ms/frame** | 3 active rules |
| Model cache hit | **~0 ms** | Repeat load of cached weights |

### Streaming

| Metric | Value | Why it matters |
|:--|:--:|:--|
| Publish latency (p99) | **0.108 ms** | With **6 slow consumers** — the producer is never blocked |
| Publish latency (median) | **0.028 ms** | |
| Encode amplification | **555 published → 172 encoded** | Encode-once caching; naïve would be 3,330 |
| 3 concurrent viewers | **388 published → 16 encoded** | vs. ~1,164 without caching |
| Thread safety | **1,589 frames, 0 errors** | 3 publishers + 5 consumers, sequences strictly monotonic |

### Alert deduplication

| Scenario | Result |
|:--|:--|
| 10 s sustained hazard @ 30 fps | **300 violations → 1 alert** — a **300× reduction** |
| Hazard clears | Auto-resolved after 5 s of silence |
| Returns within cooldown | Correctly suppressed (anti-flapping) |
| Returns after cooldown | New incident raised |

### Frontend bundle

| Chunk | Size | Gzipped |
|:--|--:|--:|
| `charts` (Recharts) | 421.9 kB | 112.6 kB |
| `react` | 164.6 kB | 53.7 kB |
| `index` (application) | 144.2 kB | 38.2 kB |
| `data` (Query + Axios) | 91.2 kB | 31.2 kB |
| CSS | 45.6 kB | 10.2 kB |

Vendor chunks are split so an application change does not invalidate the browser's cached copy
of React and the charting engine.

---

## ⚠️ Known Limitations

Stated plainly — these are real gaps, not oversights.

| Limitation | Detail |
|:--|:--|
| 🔴 **No authentication** | Every API endpoint is open. Place behind an authenticating proxy before any untrusted network. |
| 🟡 **PPE rule is a placeholder** | `PPEPlaceholderRule` ships **disabled** and always returns no violations. PPE compliance needs the detection model to emit PPE classes, which it does not. It exists so the wiring is settled and its absence is explicit. |
| 🟡 **Notification delivery not implemented** | `notification_policy.py` makes routing *decisions* for Email/SMS/Audio/Webhook. No delivery code exists — a dispatcher must consume those decisions. |
| 🟡 **Distances are in pixels** | `MinimumDistanceRule` measures pixel distance between box centres. Real-world separation needs camera calibration (a homography onto the floor plane), which the perception layer does not provide. Thresholds are per-camera. |
| 🟡 **Schema init, not migrations** | `create_all()` adds missing tables but never alters existing ones. Adopt Alembic before the schema evolves in production. |
| 🟡 **GPU-in-Docker unverified** | CPU fallback is verified working. The CUDA overlay is written but untested — no NVIDIA Container Toolkit on the development host. |
| 🟡 **Webcam passthrough is Linux-only** | Docker Desktop on Windows/macOS cannot pass a USB camera into a Linux container. Use a video file or RTSP URL there. |
| 🟡 **GPU load is a proxy** | The API exposes no GPU utilisation metric. The dashboard tile shows frame rate against a 30 fps target and is labelled as such. |
| 🟡 **Charts use a recent sample** | The API has no aggregate endpoints, so charts derive from the most recent 200 records. Headline totals use the API's exact `meta.total`. |
| 🟡 **Single camera** | The pipeline drives one source. Multi-camera needs a stream registry keyed by camera ID. |

---

## 🔮 Future Improvements

### Perception
- [ ] **Train PPE detection** (hard hat, hi-vis vest, safety boots) and enable the existing rule
- [ ] **Camera calibration** — homography onto the floor plane so distances become metres
- [ ] **Pose estimation** for fall and slip detection
- [ ] **Multi-camera support** with a stream registry and cross-camera re-identification

### Platform
- [ ] **Authentication and RBAC** — operator / supervisor / admin roles
- [ ] **Alembic migrations** for versioned, reversible schema changes
- [ ] **WebSocket alert push** to replace dashboard polling
- [ ] **Notification dispatcher** consuming the existing policy decisions
- [ ] **Aggregate API endpoints** so charts stop deriving from a sample
- [ ] **Zone configuration UI** to replace the hard-coded demonstration zones

### Operations
- [ ] **Prometheus metrics** and Grafana dashboards
- [ ] **CI/CD** with automated tests and image publishing
- [ ] **Kubernetes manifests** with horizontal scaling
- [ ] **Model registry** with versioning and A/B comparison
- [ ] **Incident reports** exportable to PDF

---

## 🤝 Contributing

Contributions are welcome. This project follows strict conventions — please read before opening
a PR.

### Getting started

```bash
git clone <repository-url>
cd AI-Warehouse-Safety-Inspector
git checkout -b feature/your-feature

# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt "lap>=0.5.12"

# Frontend
cd frontend && npm install
```

### Architectural rules

These are enforced by review and, where possible, by inspection:

| Rule | Why |
|:--|:--|
| 🚫 **No SQL outside `repositories.py`** | No router or business-logic module may import SQLAlchemy or build a query |
| 🚫 **No HTTP outside `services/`** | No React component may call Axios directly |
| 🚫 **No business logic in components** | Aggregation belongs in `utils/stats.ts`, fetching in `hooks/` |
| ✅ **Layers decouple by duck typing** | `tracking` doesn't import `detection`; `rules` doesn't import `tracking` |
| ✅ **Type hints and docstrings on every public symbol** | Google-style docstrings explaining *why*, not *what* |
| ✅ **Defensive imports for heavy dependencies** | Modules must import cleanly without Torch/OpenCV present |

### Before submitting

```bash
# Backend
python -m py_compile backend/app/**/*.py
python -c "import app.main"          # from backend/

# Frontend — both must pass
cd frontend
npx tsc --noEmit -p tsconfig.app.json
npm run build
```

### Commit convention

```
feat(alerts): add escalation cooldown per incident key
fix(streaming): prevent encode amplification with multiple viewers
docs(readme): document camera passthrough limitations
refactor(rules): extract zone geometry into reusable helpers
```

### Pull requests

1. Keep changes focused — one concern per PR
2. Explain *why*, not just *what*
3. Update documentation when behaviour changes
4. State plainly what you could **not** verify and why
5. Never introduce mock data where a real API exists

---

## 📄 License

Released under the **MIT License** — see [`LICENSE`](LICENSE).

```
Copyright (c) 2026 AI Warehouse Safety Inspector

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

<div align="center">

### Built with computer vision, clean architecture, and a healthy respect for warehouse floors.

**[⬆ Back to top](#-ai-warehouse-safety-inspector)**

</div>
