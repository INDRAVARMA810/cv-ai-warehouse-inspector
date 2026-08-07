# 4 · Deployment Topology

Both supported modes. Ports, networks, volumes and healthchecks are taken from
`docker-compose.yml` and `vite.config.ts`.

## Docker deployment

```mermaid
%%{init: {'theme':'dark','themeVariables':{'fontFamily':'Inter,system-ui,sans-serif','fontSize':'13px','lineColor':'#5E6873','primaryTextColor':'#E6E9EC','clusterBkg':'#0B0D10','clusterBorder':'#2A3138','titleColor':'#98A2AC'}}}%%
flowchart TB
    BROWSER(["👤 <b>Browser</b><br/>http://localhost:8080"])

    subgraph HOST["Docker Host"]
        direction TB

        subgraph FNET["frontend_net &lpar;bridge&rpar;"]
            FE["<b>warehouse-frontend</b><br/>nginx:1.27-alpine · 52.3 MB<br/>─────────────<br/>: 80 → host :8080<br/>healthz · wget spider<br/><i>proxy_buffering off for /stream</i>"]
        end

        subgraph BOTH[" "]
            BE["<b>warehouse-backend</b><br/>python:3.12-slim · 1.89 GB<br/>UID 10001 · tini<br/>─────────────<br/>:8000 <i>not published</i><br/>FastAPI + pipeline thread<br/>HC: /api/v1/health · start_period 120s"]
        end

        subgraph BNET["backend_net &lpar;bridge&rpar;"]
            PG[("<b>warehouse-postgres</b><br/>postgres:16-alpine<br/>─────────────<br/>:5432 → <b>127.0.0.1</b> only<br/>HC: pg_isready")]
        end

        subgraph VOL["Named Volumes"]
            V1[("postgres_data")]
            V2[("model_cache")]
            V3[("model_weights")]
        end

        BIND["📁 ./videos<br/><i>bind mount, read-only</i><br/>→ /app/videos"]
    end

    BROWSER <-->|"HTTP :8080"| FE
    FE -->|"proxy_pass<br/>backend:8000"| BE
    BE -->|"postgresql+psycopg://<br/>postgres:5432"| PG

    PG -.-> V1
    BE -.-> V2
    BE -.-> V3
    BIND -.-> BE

    BROWSER -.->|"❌ no route"| PG

    classDef client fill:#141019,stroke:#8B5CF6,stroke-width:2px,color:#E6E9EC
    classDef svc fill:#0E1620,stroke:#3B82F6,stroke-width:2px,color:#E6E9EC
    classDef store fill:#0d1a16,stroke:#10B981,stroke-width:2px,color:#E6E9EC
    classDef vol fill:#16191D,stroke:#5E6873,stroke-width:1.5px,color:#98A2AC

    class BROWSER client
    class FE,BE svc
    class PG store
    class V1,V2,V3,BIND vol
```

### Health-gated startup

`depends_on` conditions mean nothing starts before its dependency is genuinely ready:

```mermaid
%%{init: {'theme':'dark','themeVariables':{'fontFamily':'Inter,system-ui,sans-serif','fontSize':'13px','lineColor':'#5E6873','primaryTextColor':'#E6E9EC','clusterBkg':'#0B0D10','clusterBorder':'#2A3138','titleColor':'#98A2AC'}}}%%
flowchart LR
    A["postgres<br/>starting"] -->|"pg_isready<br/>interval 10s"| B["postgres<br/>✅ healthy"]
    B -->|"condition:<br/>service_healthy"| C["backend<br/>entrypoint"]
    C --> D["wait for DB<br/>WAIT_FOR_DB=90"]
    D --> E["initialize&lpar;&rpar;<br/>RUN_MIGRATIONS"]
    E --> F["seed<br/><i>optional</i>"]
    F --> G["exec uvicorn"]
    G -->|"/api/v1/health<br/>start_period 120s"| H["backend<br/>✅ healthy"]
    H -->|"condition:<br/>service_healthy"| I["frontend<br/>nginx"]
    I --> J["✅ stack ready"]

    classDef ok fill:#0d1a16,stroke:#10B981,stroke-width:2px,color:#E6E9EC
    classDef step fill:#0E1013,stroke:#2A3138,stroke-width:1.5px,color:#E6E9EC
    class B,H,J ok
    class A,C,D,E,F,G,I step
```

## Local development

```mermaid
%%{init: {'theme':'dark','themeVariables':{'fontFamily':'Inter,system-ui,sans-serif','fontSize':'13px','lineColor':'#5E6873','primaryTextColor':'#E6E9EC','clusterBkg':'#0B0D10','clusterBorder':'#2A3138','titleColor':'#98A2AC'}}}%%
flowchart TB
    DEV(["👤 <b>Browser</b><br/>http://localhost:5173<br/><i>⚠️ not 127.0.0.1 — Vite binds IPv6</i>"])

    subgraph LOCAL["Developer Machine"]
        VITE["<b>Vite dev server</b><br/>:5173 · HMR<br/>─────────────<br/>server.proxy<br/>/api → VITE_BACKEND_URL"]
        UV["<b>uvicorn --reload</b><br/>:8000<br/>app.main:app"]
        DB2[("<b>PostgreSQL</b><br/>:5432<br/><i>or SQLite file</i>")]
        VENV["📦 venv<br/>torch · ultralytics<br/>opencv · lap"]
    end

    STANDALONE["<b>run_detection.py</b><br/><i>separate process</i><br/>OpenCV window"]

    DEV <-->|"HTTP"| VITE
    VITE -->|"proxy /api"| UV
    UV -->|"DATABASE_URL"| DB2
    UV -.-> VENV
    STANDALONE -.-> VENV
    STANDALONE -.->|"❌ frames NOT visible<br/>to the API — separate<br/>StreamManager singleton"| UV

    classDef client fill:#141019,stroke:#8B5CF6,stroke-width:2px,color:#E6E9EC
    classDef svc fill:#0E1620,stroke:#3B82F6,stroke-width:2px,color:#E6E9EC
    classDef store fill:#0d1a16,stroke:#10B981,stroke-width:2px,color:#E6E9EC
    classDef warn fill:#1a1410,stroke:#F59E0B,stroke-width:2px,color:#E6E9EC

    class DEV client
    class VITE,UV svc
    class DB2 store
    class STANDALONE,VENV warn
```

## Mode comparison

| Aspect | Docker | Local |
|:--|:--|:--|
| Entry point | nginx :8080 | Vite :5173 |
| API reachability | Internal only — not published | Direct on :8000 |
| Cross-origin | Same origin via nginx | Vite `server.proxy` |
| MJPEG buffering | `proxy_buffering off` required | Vite proxy passes through |
| Database | `postgres` service on `backend_net` | Local PostgreSQL or SQLite |
| Schema creation | Entrypoint (`RUN_MIGRATIONS`) | Manual `initialize()` |
| Webcam | ⚠️ Linux hosts only — Docker Desktop cannot pass USB devices | Native support |
| GPU | Requires NVIDIA Container Toolkit + `docker-compose.gpu.yml` | Native CUDA |

## Network isolation

Two bridge networks rather than one. The **frontend has no route to PostgreSQL** — only the
backend joins both. The backend publishes no host port, so `:8080` is the single entry point
to secure.
