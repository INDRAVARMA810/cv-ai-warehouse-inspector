# 3 · Sequence — Zone Intrusion to Dashboard

What happens from a frame arriving to an operator seeing the alert. Method names and
ordering are taken from the implementation.

```mermaid
%%{init: {'theme':'dark','themeVariables':{'fontFamily':'Inter,system-ui,sans-serif','fontSize':'13px','primaryTextColor':'#E6E9EC','actorBkg':'#131619','actorBorder':'#3B82F6','actorTextColor':'#E6E9EC','signalColor':'#98A2AC','signalTextColor':'#E6E9EC','labelBoxBkgColor':'#16191D','labelBoxBorderColor':'#2A3138','noteBkgColor':'#1a1410','noteBorderColor':'#F59E0B','noteTextColor':'#E6E9EC','sequenceNumberColor':'#070809'}}}%%
sequenceDiagram
    autonumber
    participant CAM as 🎥 Camera
    participant VS as VideoStream<br/>worker thread
    participant PIPE as SafetyPipeline
    participant DET as Detector<br/>YOLOv8
    participant TRK as Tracker<br/>ByteTrack
    participant RE as RuleEngine
    participant LP as LivePersistence
    participant AM as AlertManager
    participant DB as 🗄️ PostgreSQL
    participant SM as StreamManager
    participant API as FastAPI
    participant UI as 🖥️ Dashboard

    rect rgba(59,130,246,0.07)
    Note over CAM,TRK: Frame acquisition and perception
    VS->>CAM: camera.read()
    CAM-->>VS: BGR ndarray
    VS->>PIPE: process_frame(frame)
    PIPE->>PIPE: preprocess() — resize + CLAHE
    PIPE->>DET: detect(processed)
    DET-->>PIPE: DetectionResult<br/>person @ conf 0.86
    PIPE->>TRK: update(detection_result)
    TRK-->>PIPE: TrackedObject[]<br/>track_id = 27
    end

    rect rgba(239,68,68,0.07)
    Note over RE,AM: Person enters danger zone → alert raised
    PIPE->>RE: evaluate(tracked_objects, frame_number)
    RE->>RE: RestrictedZoneRule<br/>zone.contains_point(center)
    RE-->>PIPE: RuleResult<br/>CRITICAL · machinery-bay
    PIPE-->>VS: FrameOutcome
    VS->>PIPE: render(outcome)
    PIPE-->>VS: annotated frame

    VS->>LP: record(rule_result, tracked_objects)
    LP->>LP: debounce elapsed?
    LP->>AM: process(rule_result)
    AM->>AM: incident key =<br/>rule + track + zone
    alt First occurrence
        AM-->>LP: new Alert (ACTIVE)
    else Already open
        AM->>AM: occurrence_count += 1
        AM-->>LP: [] — no new alert
        Note right of AM: 300 violations → 1 alert
    end
    end

    rect rgba(16,185,129,0.07)
    Note over LP,DB: Durable write via repositories
    LP->>DB: session_scope() → tracks.save_domain()
    LP->>DB: alerts.save_domain()
    LP->>DB: violations.save_domain(alert_id)
    DB-->>LP: committed
    end

    rect rgba(94,104,115,0.07)
    Note over VS,UI: Two independent consumers
    VS->>SM: publish(annotated)
    SM-->>VS: sequence number
    Note right of SM: never blocks —<br/>latest-frame-wins

    UI->>API: GET /stream/live
    API->>SM: get_encoded_since(seq)
    SM-->>API: JPEG bytes (encoded once)
    API-->>UI: multipart/x-mixed-replace

    UI->>API: GET /alerts?status=active
    API->>DB: repository.search()
    DB-->>API: rows
    API-->>UI: { items, meta }
    UI->>UI: badge + register + toast
    end

    rect rgba(245,158,11,0.07)
    Note over UI,DB: Operator acknowledges
    UI->>API: POST /alerts/{id}/acknowledge
    API->>DB: repository.acknowledge(id, by)
    DB-->>API: updated row
    API-->>UI: AlertResponse
    UI->>UI: invalidate queries → refetch
    end
```

## Timing characteristics

| Step | Measured | Source |
|:--|:--:|:--|
| Detection + tracking | ~38 ms/frame | 24–26 fps observed, YOLOv8n @ 640×360, RTX 4050 |
| Rule evaluation | 0.02–0.21 ms | 3 active rules, logged per frame |
| `StreamManager.publish()` | 0.028 ms median · **0.108 ms p99** | 6 concurrent slow consumers |
| Dashboard alert poll | 10–30 s | TanStack Query `refetchInterval` |
| MJPEG delivery | ≤ 1/target_fps | Generator polls at half the frame interval |

## Deduplication in practice

The `alt` branch above is the system's defining behaviour. A person standing in a danger zone
for 10 s at 30 fps produces **300 `RuleViolation` objects** but exactly **one `Alert`** — the
rest increment `occurrence_count` on the open incident. Verified: **300 → 1**.
