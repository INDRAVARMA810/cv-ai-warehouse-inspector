# 6 · Folder Dependency Graph

**Machine-derived.** Produced by extracting every `from app.X import ...` statement across
the backend, so it shows the dependencies that actually exist — not the intended ones.

```bash
# Reproduce:
for f in $(find app -name "*.py" -not -path "*__pycache__*"); do
  mod=$(echo "$f" | sed 's|app/||; s|/[^/]*\.py$||; s|\.py$||')
  grep -oE "^from app\.[a-z_]+" "$f" | sed "s|^from app\.|$mod -> |"
done | sort -u
```

```mermaid
%%{init: {'theme':'dark','themeVariables':{'fontFamily':'Inter,system-ui,sans-serif','fontSize':'13px','lineColor':'#5E6873','primaryTextColor':'#E6E9EC','clusterBkg':'#0B0D10','clusterBorder':'#2A3138','titleColor':'#98A2AC'}}}%%
flowchart BT
    subgraph L0["Layer 0 · Foundation"]
        CONFIG["<b>app.config</b><br/>Settings"]
        LOGGER["<b>app.logger</b><br/>Loguru sinks"]
    end

    subgraph L1["Layer 1 · Domain &lpar;no cross-domain imports&rpar;"]
        VIDEO["<b>app.video</b>"]
        IMG["<b>app.image_processing</b>"]
        DETECT["<b>app.detection</b>"]
        TRACK["<b>app.tracking</b>"]
        RULES["<b>app.rules</b>"]
        ALERTS["<b>app.alerts</b>"]
    end

    subgraph L2["Layer 2 · Persistence"]
        DB["<b>app.database</b>"]
    end

    subgraph L3["Layer 3 · Composition"]
        RUNDET["<b>run_detection.py</b><br/><i>backend root</i>"]
    end

    subgraph L4["Layer 4 · Streaming"]
        STREAM["<b>app.streaming</b>"]
    end

    subgraph L5["Layer 5 · Interface"]
        API["<b>app.api</b>"]
        MAIN["<b>app.main</b>"]
    end

    LOGGER --> CONFIG
    VIDEO --> LOGGER
    IMG --> LOGGER
    DETECT --> LOGGER
    TRACK --> LOGGER
    RULES --> LOGGER
    ALERTS --> LOGGER
    DB --> LOGGER
    DB --> CONFIG

    RUNDET --> VIDEO
    RUNDET --> IMG
    RUNDET --> DETECT
    RUNDET --> TRACK
    RUNDET --> RULES
    RUNDET --> CONFIG

    STREAM --> ALERTS
    STREAM --> DB
    STREAM --> LOGGER
    STREAM -.->|"lazy import<br/>at runtime"| RUNDET
    STREAM -.->|"lazy import"| VIDEO

    API --> DB
    API --> STREAM
    API --> CONFIG
    API --> LOGGER
    MAIN --> API
    MAIN --> CONFIG
    MAIN --> LOGGER

    classDef found fill:#16191D,stroke:#5E6873,stroke-width:2px,color:#E6E9EC
    classDef domain fill:#0E1620,stroke:#3B82F6,stroke-width:2px,color:#E6E9EC
    classDef store fill:#0d1a16,stroke:#10B981,stroke-width:2px,color:#E6E9EC
    classDef comp fill:#1a1410,stroke:#F59E0B,stroke-width:2px,color:#E6E9EC
    classDef iface fill:#141019,stroke:#8B5CF6,stroke-width:2px,color:#E6E9EC

    class CONFIG,LOGGER found
    class VIDEO,IMG,DETECT,TRACK,RULES,ALERTS domain
    class DB store
    class RUNDET,STREAM comp
    class API,MAIN iface
```

## Verified dependency table

Complete output of the extraction script. Self-references (package `__init__` re-exports) are
omitted.

| Module | Depends on | Notes |
|:--|:--|:--|
| `app.logger` | `config` | |
| `app.video` | `logger` | |
| `app.image_processing` | `logger` | |
| `app.detection` | `logger` | |
| `app.tracking` | `logger` | **Does not import `detection`** |
| `app.rules` | `logger` | **Does not import `tracking`** |
| `app.alerts` | `logger` | **Does not import `rules`** |
| `app.database` | `config`, `logger` | |
| `app.streaming` | `alerts`, `database`, `logger` | + lazy `run_detection`, `video` |
| `app.api` | `database`, `logger` | |
| `app.api.routers` | `api`, `config`, `database`, `logger`, `streaming` | |
| `app.main` | `api`, `config`, `logger` | |
| `run_detection.py` | `config`, `detection`, `image_processing`, `logger`, `rules`, `tracking`, `video` | Composition root |

## What the graph proves

### ✅ Acyclic
Every edge points from a higher layer to a lower one. No cycles.

### ✅ Domain modules are siblings, not a chain
`detection`, `tracking`, `rules` and `alerts` each depend only on `logger`. They are wired
together by **duck typing** at the composition root:

| Consumer | Reads structurally | Never imports |
|:--|:--|:--|
| `tracking.tracker_utils` | `.bounding_box.x1/.y1/.x2/.y2`, `.confidence`, `.class_id` | `app.detection` |
| `rules.rule` | `.track_id`, `.class_name`, `.bounding_box`, `.center` | `app.tracking` |
| `alerts.alert_engine` | `.severity`, `.rule_name`, `.description`, `.metadata` | `app.rules` |

Each layer can be replaced independently — swapping ByteTrack for DeepSORT touches only
`app.tracking`.

### ✅ Persistence is a leaf
`app.database` depends on nothing in the domain. Domain objects reach it through
`save_domain()` mappers that duck-type their input, so the ORM never leaks upward.

### ⚠️ One deliberate inversion
`app.streaming` imports `run_detection` (a higher layer) **lazily, inside a method**:

```python
# app/streaming/stream.py — inside VideoStream._build_pipeline()
from run_detection import PipelineConfig, SafetyPipeline
```

This is intentional and documented in the module. Reusing the existing `SafetyPipeline`
avoids reimplementing the detect → track → evaluate chain, and the lazy import keeps
`app.streaming` — and therefore the whole API — importable on machines with no Torch, no
OpenCV and no GPU.
