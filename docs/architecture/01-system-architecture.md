# 1 · High-Level System Architecture

Every element below is verified against the repository. Edge labels state the **actual
transport or call mechanism**, not a generic association.

```mermaid
%%{init: {'theme':'dark','themeVariables':{'fontFamily':'Inter,system-ui,sans-serif','fontSize':'14px','lineColor':'#5E6873','primaryTextColor':'#E6E9EC','clusterBkg':'#0B0D10','clusterBorder':'#2A3138','titleColor':'#98A2AC'}}}%%
flowchart TB
    subgraph EDGE["Capture Edge"]
        CAM["<b>Video Source</b><br/><i>webcam index · file · RTSP</i><br/>STREAM_SOURCE"]
    end

    subgraph BACKEND["Backend Container — FastAPI + Pipeline &lpar;one process&rpar;"]
        direction TB

        subgraph WORKER["Pipeline Worker Thread — app.streaming.stream.VideoStream"]
            direction LR
            CV["<b>OpenCV</b><br/>app.video.Camera<br/>app.image_processing"]
            YOLO["<b>YOLOv8</b><br/>app.detection<br/>Ultralytics"]
            BT["<b>ByteTrack</b><br/>app.tracking<br/>identity assignment"]
            RULES["<b>Rule Engine</b><br/>app.rules<br/>zones · distance · occupancy"]
            ALERTS["<b>Alert Engine</b><br/>app.alerts<br/>dedup · cooldown · escalate"]
            CV -->|"BGR ndarray"| YOLO
            YOLO -->|"DetectionResult"| BT
            BT -->|"TrackedObject[]"| RULES
            RULES -->|"RuleResult"| ALERTS
        end

        SM["<b>StreamManager</b><br/>app.streaming.stream_manager<br/><i>latest-frame-wins · thread-safe</i>"]
        ENC["<b>FrameEncoder</b><br/>app.streaming.frame_encoder<br/><i>encode once per sequence</i>"]
        LP["<b>LivePersistence</b><br/>app.streaming.persistence<br/><i>debounced writes</i>"]
        REPO["<b>Repositories</b><br/>app.database.repositories<br/><i>only module issuing SQL</i>"]
        API["<b>FastAPI Routers</b><br/>app.api.routers<br/>alerts · violations · tracks<br/>system · stream · health"]
        MJPEG["<b>MJPEG Generator</b><br/>app.streaming.mjpeg<br/>multipart/x-mixed-replace"]
    end

    subgraph DATA["Database Container"]
        PG[("<b>PostgreSQL 16</b><br/>alert_records<br/>violation_records<br/>track_records<br/>system_events")]
    end

    subgraph WEB["Frontend Container"]
        NGINX["<b>nginx 1.27</b><br/>static bundle +<br/>reverse proxy"]
        REACT["<b>React Dashboard</b><br/>8 routes · TanStack Query<br/>Recharts · Tailwind"]
    end

    BROWSER(["👤 <b>Operator Browser</b>"])

    CAM -->|"cv2.VideoCapture.read&lpar;&rpar;"| CV
    ALERTS -->|"Alert objects"| LP
    RULES -->|"RuleViolation[]"| LP
    BT -->|"TrackedObject[]"| LP
    WORKER -->|"annotated frame<br/>manager.publish&lpar;&rpar;"| SM

    LP -->|"save_domain&lpar;&rpar;<br/>via session_scope"| REPO
    REPO -->|"SQLAlchemy 2.0<br/>psycopg 3"| PG

    SM -->|"get_encoded_since&lpar;seq&rpar;"| ENC
    ENC -->|"JPEG bytes"| MJPEG
    API -->|"Depends&lpar;get_*_repository&rpar;"| REPO
    API -->|"get_video_stream&lpar;&rpar;"| SM

    MJPEG -->|"HTTP 200<br/>infinite multipart"| NGINX
    API -->|"JSON · /api/v1/*"| NGINX
    NGINX -->|"serves bundle"| REACT
    REACT -->|"axios · fetch"| BROWSER
    NGINX <-->|"HTTP :8080"| BROWSER

    classDef capture fill:#1a1410,stroke:#F59E0B,stroke-width:2px,color:#E6E9EC
    classDef vision fill:#0E1620,stroke:#3B82F6,stroke-width:2px,color:#E6E9EC
    classDef safety fill:#1a1012,stroke:#EF4444,stroke-width:2px,color:#E6E9EC
    classDef infra fill:#0E1013,stroke:#2A3138,stroke-width:1.5px,color:#E6E9EC
    classDef store fill:#0d1a16,stroke:#10B981,stroke-width:2px,color:#E6E9EC
    classDef client fill:#141019,stroke:#8B5CF6,stroke-width:2px,color:#E6E9EC

    class CAM capture
    class CV,YOLO,BT vision
    class RULES,ALERTS safety
    class SM,ENC,LP,REPO,API,MJPEG,NGINX infra
    class PG store
    class REACT,BROWSER client
```

## Communication matrix

| From | To | Mechanism | Verified at |
|:--|:--|:--|:--|
| Video source | OpenCV | `cv2.VideoCapture.read()` | `app/video/camera.py` |
| OpenCV | YOLOv8 | in-process call, BGR `ndarray` | `run_detection.py` · `SafetyPipeline.process_frame` |
| YOLOv8 | ByteTrack | `DetectionResult` object | `run_detection.py:process_frame` |
| ByteTrack | Rule Engine | `TrackedObject[]` (duck-typed) | `run_detection.py:process_frame` |
| Rule Engine | Alert Engine | `RuleResult` (duck-typed) | `persistence.py:record` |
| Pipeline | StreamManager | `manager.publish(annotated)` | `stream.py:384` |
| Pipeline | LivePersistence | `persistence.record(...)` | `stream.py:382` |
| LivePersistence | Repositories | `RepositoryBundle.for_session` | `persistence.py:97` |
| Repositories | PostgreSQL | SQLAlchemy 2.0 + psycopg 3 | `app/database/repositories.py` |
| StreamManager | MJPEG | `get_encoded_since(seq)` polling | `app/streaming/mjpeg.py` |
| Routers | Repositories | `Depends(get_*_repository)` | `app/api/dependencies.py` |
| Routers | StreamManager | `get_video_stream()` singleton | `app/api/routers/stream.py:65` |
| nginx | Backend | HTTP reverse proxy, `proxy_buffering off` for stream | `frontend/nginx.conf.template` |
| Browser | nginx | HTTP :8080 (single origin) | `docker-compose.yml` |

## Architectural invariants

1. **The pipeline runs inside the API process.** `StreamManager` is a process-wide singleton;
   frames produced by a separate `run_detection.py` process are *not* visible to the API.
2. **Only `repositories.py` issues SQL.** No router imports SQLAlchemy — verified by grep.
3. **The producer never blocks.** `publish()` never queues; encoding happens outside the
   producer's lock, so a slow viewer cannot throttle inference.
4. **Layers decouple by duck typing.** `rules` does not import `tracking`; `alerts` does not
   import `rules`. Confirmed by the import graph in [diagram 6](06-folder-dependencies.md).
