# Showcase Assets

Everything needed to present this project on GitHub, LinkedIn, a resume, and in a placement
interview.

> **Accuracy rule applied throughout:** every claim below was checked against the
> implementation. Where a capability does not exist, it is marked ⛔ rather than described.
> Measured numbers come from this repository's own verification runs on an **RTX 4050 Laptop
> GPU** — always state the hardware when quoting them.

---

## Table of Contents

- [1 · Screenshot Checklist](#1--screenshot-checklist)
- [2 · Presentation-Layer Improvements](#2--presentation-layer-improvements)
- [3 · Demo Narration Script](#3--demo-narration-script)
- [4 · Recording Checklist](#4--recording-checklist)
- [5 · GitHub Assets](#5--github-assets)
- [6 · Resume Assets](#6--resume-assets)
- [7 · LinkedIn Assets](#7--linkedin-assets)
- [8 · Verification Log](#8--verification-log)

---

## 1 · Screenshot Checklist

Capture at **1680×1050 or wider**, dark mode, browser chrome hidden (`F11`), zoom at 100%.
Save into `screenshots/` using the filenames below so the README embeds resolve.

### Preparation

```bash
# 1. Seed data so no panel is empty
SEED_DEMO_DATA=true docker compose up -d --build

# 2. Warm the stream so the feed is live before you capture
curl -s "http://localhost:8080/api/v1/stream/status"
```

Open `http://localhost:8080` and let the feed connect (first start loads the model — allow
up to 2 minutes).

### The eleven captures

| # | File | Route / target | Must be visible | Notes |
|:--:|:--|:--|:--|:--|
| 1 | `dashboard.png` | `/` | Live feed, 6 KPI tiles, Alerts by Hour, Alerts by Severity | **Hero shot.** Wait for KPIs to show real numbers, not `––` |
| 2 | `live-webcam.png` | `/live` | Camera 01 — Main Floor, side rail with Live Alerts | Run with `STREAM_SOURCE=0` for a real webcam |
| 3 | `alerts.png` | `/alerts` | Register + severity badges + filter bar | Click a row so the **detail drawer** is open with Acknowledge/Resolve |
| 4 | `violations.png` | `/violations` | Violation Log with severity column | Set a severity filter so filtering is visibly in use |
| 5 | `tracks.png` | `/tracks` | Tracked Objects, confidence bars, dwell column | Sort by Frames descending |
| 6 | `analytics.png` | `/analytics` | Highlights row + Alerts by Hour + all four distribution charts | Scroll so ≥3 charts are in frame |
| 7 | `api-docs.png` | `/docs` | Swagger UI with `alerts` and `stream` groups expanded | Expand `POST /alerts/search` to show the schema |
| 8 | `docker-containers.png` | terminal | `docker compose ps` — 3 containers **(healthy)** | Command shown below |
| 9 | `postgres-tables.png` | terminal | 4 tables + a row count | Command shown below |
| 10 | `yolo-overlay.png` | `/live` (cropped) | Bounding boxes, `#track_id class conf`, zone rectangles, violation list, FPS/CUDA HUD | **Strongest single image.** Crop to the viewport only |
| 11 | `architecture.png` | `docs/diagrams/` | System architecture diagram | Export the SVG to PNG |

### Terminal commands for #8 and #9

```bash
# 8 — container health
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"

# 9 — schema and row counts
docker compose exec postgres psql -U postgres -d warehouse_ai -c "\dt"
docker compose exec postgres psql -U postgres -d warehouse_ai -c \
  "SELECT 'alerts' AS table, COUNT(*) FROM alert_records
   UNION ALL SELECT 'violations', COUNT(*) FROM violation_records
   UNION ALL SELECT 'tracks', COUNT(*) FROM track_records
   UNION ALL SELECT 'events', COUNT(*) FROM system_events;"
```

### Architecture PNG export

```bash
npm install --no-save @mermaid-js/mermaid-cli
npx mmdc -i docs/architecture/01-system-architecture.md \
         -o screenshots/architecture.png -b "#070809" -w 2000
```

### ⛔ Do not attempt

| Shot | Why |
|:--|:--|
| Webcam **inside Docker** | Docker Desktop on Windows/macOS cannot pass a USB camera into a Linux container. Capture the webcam shot from a **local** run, or use `STREAM_SOURCE=/app/videos/*.mp4` in Docker. |
| A "login" or "user management" screen | No authentication exists. |
| Email/SMS notification settings | Routing **policy** exists; there is no delivery implementation. |
| PPE detection results | `PPEPlaceholderRule` ships disabled and returns nothing. |

---

## 2 · Presentation-Layer Improvements

Only cosmetic changes to what already renders. **No new features.** Ordered by impact per
minute of effort.

### 🔴 High impact

**1. Seed data before every capture.** Empty panels dominate a screenshot. With
`SEED_DEMO_DATA=true` the register, charts and tables all populate. *(Config, not code.)*

**2. Warm the stream before capturing.** A cold dashboard shows *"Acquiring feed — starting
capture pipeline and loading the detection model"* with a spinner. Hit
`/api/v1/stream/status` first and wait for `available: true`, or the hero shot shows a
loading state. *(Verified — this exact copy renders on first load.)*

**3. Unify duplicated panel subtitles.** The same chart is described two different ways on
Dashboard vs. Analytics, which looks careless side by side in a carousel:

| Panel | Dashboard | Analytics |
|:--|:--|:--|
| Occupancy Trend | `Objects on floor, trailing 8 h` | `Objects on floor, trailing 8 hours` |
| Average Dwell Time | `Mean and peak, by class` | `Mean and peak, by object class` |

Pick one wording for each. *(Two string edits.)*

**4. Replace the inline magic number in the dashboard footer.**
`DashboardPage.tsx:317` reads:

```tsx
Charts derive from the most recent {200} records.
```

The literal `{200}` is hard-coded next to a `SAMPLE = 200` constant that already exists in
`useDashboardData.ts`. Export and reference it so the sentence cannot drift from the query.

### 🟡 Medium impact

**5. Capture on the hour-boundary for a fuller Alerts-by-Hour chart.** The chart buckets a
trailing 24 h. Seeded demo alerts cluster in the last hour, so most buckets are empty and the
chart reads as sparse. Either capture after running the pipeline for a while, or accept it and
frame the Analytics shot on the distribution charts instead.

**6. Mind the `Workers` KPI.** It counts **person tracks seen in the last 15 minutes**, read
from the database. Live persistence *does* write tracks, so this populates during a live run —
but on a freshly seeded database with no pipeline running it correctly shows `0`. For the hero
shot, have the stream running so the number is non-zero.

**7. Widen the browser to ≥1680px.** Several grids collapse below `xl`: the KPI row goes from
6-across to 3-across, and the Analytics grid drops to a single column. The 6-across KPI row is
the most recognisably "control room" element on the page.

### 🟢 Polish

**8. Consistent clock in every shot.** The top bar shows a live wall clock. Capture the whole
set in one sitting so timestamps are within minutes of each other — mismatched clocks across a
carousel look like screenshots from different builds.

**9. Close the notification dropdown** before capturing anything other than the notification
shot; it overlays the top-right KPI tiles.

**10. Prefer `Resolved`/`Acknowledged` rows in at least one shot.** An all-red register reads
as a broken system. The seeded data already includes one of each status — make sure the sort
shows the mix.

> **Not recommended:** do not fabricate KPI values, invent extra cameras, or mock a login
> screen for the screenshots. If asked in an interview whether a screenshot is real, the answer
> must be yes.

---

## 3 · Demo Narration Script

**Target: 2 min 30 s.** Timings are cumulative. Written to be read aloud at ~150 wpm.

---

### `0:00 – 0:20` — Problem Statement

> "Warehouses run on constant, well-understood hazards — people walking into machinery
> envelopes, forklifts passing too close to pedestrians, zones going over safe occupancy.
> The controls we already have are mostly painted lines and human attention, and human
> attention does not scale across three shifts and a dozen cameras."

### `0:20 – 0:40` — Existing Problems

> "Two things usually go wrong when teams automate this. First, detection alone isn't safety —
> a bounding box doesn't tell you whether someone crossed a line. Second, and this is the one
> that kills adoption: naive systems fire an alert on every frame. A person standing in a
> danger zone for ten seconds at thirty frames per second generates three hundred alerts.
> Operators stop looking."

### `0:40 – 1:05` — Proposed Solution & Architecture

> "So this system is built as a pipeline, not a model. A frame comes off the camera through
> OpenCV, YOLOv8 detects objects, ByteTrack assigns each one a stable identity across frames,
> and a rule engine evaluates that against configured danger and restricted zones.
>
> The important part is what happens next. An alert engine groups violations by incident —
> rule, plus track ID, plus zone — so those three hundred violations collapse into **one**
> durable incident with an occurrence counter. Measured: a three-hundred-to-one reduction.
> That incident is written to PostgreSQL through a repository layer, served by FastAPI, and
> rendered on a React dashboard."

### `1:05 – 1:50` — Live Demonstration

> *(Dashboard on screen)*
> "This is the operations overview. Live annotated feed top-left — those are real bounding
> boxes with track IDs and confidence, drawn by the pipeline, and the red rectangle is a
> configured danger zone. Top right, every subsystem reporting: PostgreSQL, FastAPI, the YOLO
> detector, ByteTrack, the rule engine, the MJPEG stream.
>
> *(Step into the danger zone)*
> "Watch what happens when I enter the zone. The overlay flags it immediately, the violation
> counter increments — and note the alert count goes up by **one**, not by thirty per second.
>
> *(Navigate to Alerts, open a row)*
> "Here's that incident in the register. Severity, track ID, rule, zone, timestamp. Opening it
> shows the full audit trail and the occurrence count. I can acknowledge it — that records a
> human saw it — and resolve it separately, once the hazard actually clears."

### `1:50 – 2:10` — Technologies & Challenges

> "Python 3.12, FastAPI, PyTorch with YOLOv8, OpenCV, SQLAlchemy over PostgreSQL, and a React
> and TypeScript front end. The whole thing is containerised with Docker Compose.
>
> The hardest engineering problem wasn't detection — it was the streaming layer. MJPEG viewers
> are slow consumers and the inference loop is a fast producer. If a viewer can apply
> back-pressure, your safety pipeline stalls because someone opened a browser tab. So the
> frame hand-off is latest-frame-wins and lock-free from the producer's side: measured
> publish latency stays at a tenth of a millisecond at the 99th percentile with six slow
> consumers attached."

### `2:10 – 2:30` — Results & Future Scope

> "End to end it runs at twenty-four to twenty-six frames per second on an RTX 4050, with rule
> evaluation under a fifth of a millisecond per frame. Alerts deduplicate three hundred to one.
> Three containers, health-gated startup, and a verification suite that checks the stack after
> deployment.
>
> What's next: PPE detection — hard hats and hi-vis — where the rule is already wired and
> waiting on a trained model; camera calibration so distances become metres instead of pixels;
> and authentication, which the system does not have yet."

---

### Interview add-ons

Short, honest answers to the questions this demo invites.

| Question | Answer |
|:--|:--|
| *"Is this production-ready?"* | "The pipeline and API are. It has no authentication, so it would sit behind an authenticating proxy on a trusted network. And schema changes need Alembic — right now it only creates missing tables." |
| *"Why MJPEG and not WebRTC?"* | "MJPEG renders in a plain `<img>` in every browser with no client-side code. For a monitoring dashboard on a LAN, that reliability beats WebRTC's efficiency. It's the pragmatic choice, not the sophisticated one." |
| *"What would you change?"* | "Distances are in pixels, which means thresholds are per-camera. Proper homography onto the floor plane would make them metres and make the rule portable." |
| *"What broke during the build?"* | "ByteTrack's integration. I'd written it against the documented API and mock-tested it. When I ran it against the real Ultralytics build, the constructor signature had changed and the results object needed boolean-mask indexing my adapter didn't implement. It would have crashed on the first frame." |

---

## 4 · Recording Checklist

**Total target: 2:30.** Record in segments and cut — do not attempt one take.

### Before you press record

- [ ] `SEED_DEMO_DATA=true docker compose up -d --build`, all 3 containers `(healthy)`
- [ ] Stream warmed — `/api/v1/stream/status` shows `available: true`
- [ ] Browser at **1920×1080**, fullscreen (`F11`), 100% zoom
- [ ] Notifications, chat apps and the taskbar hidden
- [ ] Danger zone (`machinery-bay`) is in your webcam's frame — check the overlay first
- [ ] Rehearse the walk-in once; know exactly where the zone boundary is on screen
- [ ] Audio: one take of narration separately, then lay video under it

### Ordered shot list

| # | Time | Screen | Action | Narration beat |
|:--:|:--|:--|:--|:--|
| 1 | `0:00–0:12` | Architecture diagram (`docs/diagrams/`) | Slow zoom on the pipeline row | Problem statement |
| 2 | `0:12–0:25` | Terminal | `docker compose ps` — 3 healthy | Existing problems |
| 3 | `0:25–0:45` | Dashboard `/` | Static. Let charts animate in | Solution + architecture |
| 4 | `0:45–0:55` | Dashboard, cursor on subsystem board | Hover each subsystem row | "every subsystem reporting" |
| 5 | `0:55–1:15` | `/live` full-bleed | **Stand outside the zone**, then walk in | "watch what happens" |
| 6 | `1:15–1:22` | `/live`, cropped on viewport | Hold still inside the zone ~5 s | "one, not thirty per second" |
| 7 | `1:22–1:35` | `/alerts` | Show register, then **click the new row** | "here's that incident" |
| 8 | `1:35–1:45` | Alert detail drawer | Click **Acknowledge**, then **Resolve** | "acknowledge… resolve separately" |
| 9 | `1:45–1:55` | `/analytics` | Scroll slowly through charts | Technologies |
| 10 | `1:55–2:05` | `/docs` (Swagger) | Expand `POST /alerts/search` | "FastAPI, OpenAPI" |
| 11 | `2:05–2:15` | Terminal | `psql \dt` + row counts | Challenges |
| 12 | `2:15–2:30` | Dashboard `/` | Return to hero, hold | Results + future scope |

### Webcam actions — exact sequence

1. **Frame check** — stand outside the zone. Confirm your box is green and no violation lists.
2. **Approach** — walk slowly toward the boundary. *Do not rush; the tracker needs a few frames
   to hold your ID.*
3. **Cross** — step fully inside `machinery-bay`. Box turns red, `[CRITICAL] person (track N)
   entered danger zone 'machinery-bay'` appears in the overlay list.
4. **Hold — 5 seconds.** This is the money shot: the alert count stays at 1 while the
   occurrence count climbs.
5. **Exit** — step out. Overlay clears.
6. **Do not re-enter within 30 s** — the cooldown will suppress a second alert, which looks
   like a bug on camera unless you're explaining it deliberately.

> 💡 **If you have no webcam**, `videos/warehouse-demo.mp4` drives the same pipeline. You lose
> the live walk-in but keep every overlay. Say "recorded footage" rather than implying live.

### Trigger timing

| Violation | How to trigger | Appears as |
|:--|:--|:--|
| Zone intrusion | Walk into `machinery-bay` | `CRITICAL` |
| Restricted zone | Walk into `loading-dock` | `HIGH` |
| Occupancy | Get 6+ people in `loading-dock` | `MEDIUM` — usually impractical solo |
| Proximity | ⛔ Needs a detected `forklift` — not triggerable on a webcam |

Realistically, solo: **zone intrusion → restricted zone** covers both severity tiers.

---

## 5 · GitHub Assets

### Social preview image

GitHub's Open Graph card. **Settings → General → Social preview.**

| Spec | Value |
|:--|:--|
| Dimensions | **1280 × 640 px** (2:1) |
| Safe area | Keep content inside the centre **1200 × 600** — edges crop in some clients |
| Format | PNG, < 1 MB |
| File | `screenshots/social-preview.png` |

**Composition:**

```
┌──────────────────────────────────────────────────────┐
│  bg #070809                                          │
│                                                      │
│   AI Warehouse Safety Inspector          ┌─────────┐ │
│   ───────────────────────────            │ cropped │ │
│   Real-time CV safety monitoring         │  YOLO   │ │
│                                          │ overlay │ │
│   YOLOv8 · ByteTrack · FastAPI           │ w/ boxes│ │
│   PostgreSQL · React · Docker            └─────────┘ │
│                                                      │
└──────────────────────────────────────────────────────┘
      55% text left            45% screenshot right
```

Use the **cropped YOLO overlay** (shot #10) on the right — boxes and a red danger zone read
instantly at thumbnail size. Avoid the full dashboard here; it turns to mush below 400px wide.

### Repository banner

| Spec | Value |
|:--|:--|
| Dimensions | **1200 × 300 px** (4:1) |
| Placement | Top of README, inside the existing `<div align="center">` |
| File | `screenshots/banner.png` |

Optional — the current badge-based header already reads well. Only add a banner if you produce
a genuinely clean one; a mediocre banner is worse than none.

### Video thumbnail

| Spec | Value |
|:--|:--|
| Dimensions | **1280 × 720 px** (16:9) |
| Composition | Full-bleed `/live` screenshot, darkened 40%, with 3–4 words of overlay text |
| Text | *"Real-Time Warehouse Safety AI"* — max 4 words, ≥ 60px |
| Focal point | A red bounding box inside a danger zone, upper-left third |

### README image order

The order that survives a 15-second skim:

1. **Badges** *(already present)*
2. **Demo GIF** — motion first; it proves the thing runs
3. **Dashboard screenshot** — the hero
4. **YOLO overlay (cropped)** — proves the CV is real, not a UI mockup
5. **Architecture diagram** — for the reader who is now interested
6. **Alerts + detail drawer** — proves it's an application, not a script
7. **Analytics** — proves data depth
8. **API docs** — proves the backend is real
9. *(Everything else lives in `docs/`)*

> **Rule of thumb:** anything past image 5 is for someone already reading properly. Front-load
> motion and evidence.

---

## 6 · Resume Assets

### One-line summary

> Real-time computer-vision safety platform that detects, tracks, and evaluates warehouse
> hazards against configurable zones, deduplicating 300 per-frame violations into a single
> actionable incident.

**Shorter (for a header line):**

> Real-time warehouse safety monitoring: YOLOv8 + ByteTrack + FastAPI + React, containerised.

### Resume bullet points

Written to lead with impact and carry a verified number.

> • Engineered an end-to-end computer-vision safety pipeline (**OpenCV → YOLOv8 → ByteTrack →
> rule engine → alert engine**) sustaining **24–26 FPS** on GPU with sub-millisecond rule
> evaluation, cutting alert volume **300:1** through incident deduplication, cooldown, and
> graded escalation.

> • Built a thread-safe MJPEG streaming layer with latest-frame-wins hand-off and
> encode-once caching, holding **p99 publish latency at 0.108 ms with six concurrent
> consumers** — guaranteeing viewers can never apply back-pressure to the inference loop.

> • Delivered the full stack — **FastAPI** REST API (13 endpoints, OpenAPI-documented),
> **PostgreSQL** persistence behind a repository pattern, and a **React + TypeScript**
> operations dashboard — containerised with **Docker Compose** across three health-gated
> services on isolated networks.

**Optional fourth**, if the role is frontend-leaning:

> • Designed a high-density dark-mode control-room dashboard (8 routes, 6 chart types) with
> complete loading, empty, error and live states across every widget, server-driven pagination
> and filtering, and an auto-reconnecting live video panel with exponential backoff.

### ATS-friendly technologies list

Plain text, comma-separated, no graphics — parses reliably.

```
Python, FastAPI, PyTorch, YOLOv8, Ultralytics, OpenCV, ByteTrack, Computer Vision,
Object Detection, Multi-Object Tracking, Real-Time Video Processing, MJPEG Streaming,
PostgreSQL, SQLAlchemy, psycopg, Pydantic, REST API, OpenAPI, Repository Pattern,
React, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts, Axios,
Docker, Docker Compose, nginx, CUDA, Git, Multithreading, Clean Architecture
```

**Grouped variant** for a skills section:

| Category | Technologies |
|:--|:--|
| Languages | Python 3.12, TypeScript, SQL |
| Computer Vision | YOLOv8, Ultralytics, ByteTrack, OpenCV, PyTorch, CUDA |
| Backend | FastAPI, Pydantic, SQLAlchemy 2.0, PostgreSQL, psycopg 3, Uvicorn |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts |
| Infrastructure | Docker, Docker Compose, nginx |
| Practices | Clean architecture, repository pattern, dependency injection, thread safety |

---

## 7 · LinkedIn Assets

### Post

> **Most computer-vision safety demos would get an operator fired.**
>
> Not because the detection is wrong — because of what happens next.
>
> A person stands in a danger zone for 10 seconds. At 30 FPS, that's 300 rule violations. Send
> 300 alerts and the operator mutes the system by lunchtime. The model was right and the
> product still failed.
>
> So when I built **AI Warehouse Safety Inspector**, most of the engineering went into the
> layer after detection:
>
> 🎯 **Detection → Tracking → Rules** — YOLOv8 finds objects, ByteTrack gives them stable
> identities across frames, and a rule engine evaluates them against configured danger and
> restricted zones.
>
> 🔔 **300 violations → 1 incident.** Alerts group by rule + track + zone, deduplicate,
> cool down to prevent flapping, and escalate gradually if a hazard persists. One durable
> incident with an occurrence counter — not a firehose.
>
> ⚡ **The hard part was streaming.** MJPEG viewers are slow consumers; the inference loop is a
> fast producer. If a viewer can push back, your safety pipeline stalls because someone opened
> a browser tab. Latest-frame-wins hand-off, lock-free on the producer side: p99 publish
> latency 0.108 ms with 6 concurrent viewers.
>
> 📊 **The whole stack:** FastAPI + PostgreSQL behind a repository pattern, a React control-room
> dashboard, three Docker containers with health-gated startup on isolated networks.
>
> Running at **24–26 FPS on an RTX 4050**, with rule evaluation under 0.2 ms per frame.
>
> Two things it does **not** do yet, because I'd rather say so: no authentication, and PPE
> detection is wired but waiting on a trained model.
>
> Building the model is the easy half. Building the thing an operator will still be using in
> week three is the other half.
>
> Repo in comments 👇
>
> #ComputerVision #MachineLearning #Python #YOLOv8 #FastAPI #React #Docker #PostgreSQL

> 💡 **Post-craft notes:** hook is the first line — LinkedIn truncates around 210 characters,
> so "would get an operator fired" must land above the fold. Put the repo link in the **first
> comment**, not the post body (link posts get throttled). Attach the demo GIF or a 30-second
> native video; native video outperforms an external link.

### Carousel — 8 slides

**1080 × 1080 px**, dark background `#070809`, Inter for headings, JetBrains Mono for numbers.

| # | Headline | Body | Visual |
|:--:|:--|:--|:--|
| **1** | **300 alerts.<br/>One hazard.** | Why most CV safety demos fail in week three | Cropped YOLO overlay, red danger zone. Big type. |
| **2** | **The problem** | Painted lines and human attention don't scale across 3 shifts and 12 cameras | Warehouse photo or the dark dashboard, dimmed |
| **3** | **Detection isn't safety** | A bounding box doesn't tell you someone crossed a line. You need identity, zones, and rules. | Detection → Tracking → Rules, 3 chevrons |
| **4** | **The pipeline** | OpenCV → YOLOv8 → ByteTrack → Rule Engine → Alert Engine → PostgreSQL | Architecture diagram, simplified |
| **5** | **300 → 1** | Group by rule + track + zone. Deduplicate. Cool down. Escalate gradually. | Big `300:1`, mono. Alert register screenshot beneath |
| **6** | **The hard part: streaming** | Viewers must never back-pressure the inference loop.<br/>**p99 0.108 ms · 6 consumers** | Latest-frame-wins diagram or the live panel |
| **7** | **Full stack, containerised** | FastAPI · PostgreSQL · React · Docker<br/>3 services · health-gated · isolated networks | `docker compose ps` output, all healthy |
| **8** | **What's next** | PPE detection · camera calibration · authentication<br/>*Repo link* | Dashboard hero + call to action |

> Slide 1 does all the work — it must be readable as a 400px thumbnail. Slide 5 is the one
> people screenshot.

### Short video caption

> 300 rule violations. One alert.
>
> Watch what happens when I step into a danger zone: YOLOv8 detects, ByteTrack holds the
> identity, the rule engine flags the intrusion — and the alert engine collapses 10 seconds of
> continuous violation into a single incident with an occurrence counter.
>
> Real-time on an RTX 4050. Full stack, containerised.
>
> #ComputerVision #YOLOv8 #Python #MachineLearning

### Hashtags

**Primary (use 5–8 — LinkedIn favours focus):**

```
#ComputerVision #MachineLearning #Python #YOLOv8 #DeepLearning
#FastAPI #React #Docker
```

**Extended pool, by angle:**

| Angle | Tags |
|:--|:--|
| Technical | `#PyTorch` `#OpenCV` `#ObjectDetection` `#ObjectTracking` `#AI` `#RealTimeAI` |
| Stack | `#PostgreSQL` `#TypeScript` `#SQLAlchemy` `#RESTAPI` `#FullStackDevelopment` |
| Domain | `#IndustrialAutomation` `#WarehouseSafety` `#WorkplaceSafety` `#Manufacturing` `#Logistics` `#IndustrialIoT` |
| Career | `#SoftwareEngineering` `#OpenSource` `#BuildInPublic` `#100DaysOfCode` |

---

## 8 · Verification Log

Every claim above was checked against the implementation before being written.

### ✅ Verified present

| Claim | Verified by |
|:--|:--|
| 6 KPI tiles: Workers, Active Alerts, Critical Alerts, Violations Today, Average FPS, GPU Load | `grep 'label='` in `DashboardPage.tsx` |
| 8 dashboard routes | `App.tsx` route table |
| 13 API endpoints, `/docs` + `/redoc` | Live OpenAPI schema dump |
| 3 containers: `warehouse-postgres`, `warehouse-backend`, `warehouse-frontend` | `docker-compose.yml` |
| 4 tables: `alert_records`, `violation_records`, `track_records`, `system_events` | `models.py` `__tablename__` |
| Live persistence writes tracks, alerts and violations | `persistence.py:100,106,108` |
| Windows webcam support via `CAMERA_BACKEND` → `CAP_DSHOW` | `app/video/camera.py:52` |
| Danger zone `machinery-bay`, restricted `loading-dock` | `run_detection.py` `_install_zones` |
| Acknowledge / Resolve UI + endpoints | `AlertDetail.tsx`, `routers/alerts.py` |
| 24–26 FPS, p99 0.108 ms, 300:1 dedup | Session verification runs, RTX 4050 |

### ⛔ Deliberately excluded

| Not claimed | Reason |
|:--|:--|
| Login / auth screenshot | No authentication exists |
| Email or SMS notifications | Policy decisions only — no delivery code |
| PPE detection results | `PPEPlaceholderRule` disabled, returns nothing |
| Webcam inside Docker | Docker Desktop can't pass USB cameras to Linux containers |
| Multi-camera views | Pipeline drives a single source |
| Real-world distances in metres | `MinimumDistanceRule` measures pixels |
| GPU utilisation % as a true metric | Dashboard shows FPS-vs-30-target, labelled as a proxy |
| Proximity violation in the recording plan | Needs a detected forklift — not triggerable on a webcam |

### ⚠️ State honestly if asked

- **GPU-in-Docker is untested** — CPU fallback is verified; the CUDA overlay is written but was
  never run (no NVIDIA Container Toolkit on the dev host).
- **Charts derive from a 200-record sample**, not full aggregates. Headline totals are exact.
- **Schema initialisation only** — `create_all()` adds missing tables, never alters existing
  ones. Alembic is not yet a dependency.
