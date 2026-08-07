# Architecture Documentation

Engineering diagrams for the **AI Warehouse Safety Inspector**, derived from the
implementation rather than from intent.

## Diagrams

| # | Diagram | Answers |
|:--:|:--|:--|
| 1 | [System Architecture](01-system-architecture.md) | What are the components and how do they communicate? |
| 2 | [Data Flow](02-data-flow.md) | What happens to a single frame, end to end? |
| 3 | [Sequence — Zone Intrusion](03-sequence-alert.md) | What happens when someone enters a danger zone? |
| 4 | [Deployment](04-deployment.md) | How does it run in Docker vs. locally? |
| 5 | [Components](05-components.md) | What does each backend module own? |
| 6 | [Folder Dependencies](06-folder-dependencies.md) | Which module imports which? |

SVG exports live in [`docs/diagrams/`](../diagrams/).

## Verification method

Nothing here was written from memory or assumption. Each diagram traces to a verifiable source:

| Diagram | Derived from |
|:--|:--|
| System architecture | Import graph + call sites in `stream.py`, `persistence.py`, `routers/` |
| Data flow | `SafetyPipeline.process_frame()` and the `VideoStream._run()` worker loop |
| Sequence | Method names read from `stream.py`, `persistence.py`, `alert_manager.py`, `repositories.py` |
| Deployment | `docker-compose.yml`, `nginx.conf.template`, `vite.config.ts` |
| Components | `find app -name "*.py"` plus each module's public exports |
| Dependencies | [`scripts/extract-dependencies.sh`](../../scripts/extract-dependencies.sh) — machine-generated |

Regenerate the dependency graph after any refactor:

```bash
./scripts/extract-dependencies.sh
```

## Conventions

**Notation**

| Element | Meaning |
|:--|:--|
| `A --> B` | Direct, compile-time dependency or synchronous call |
| `A -.-> B` | Lazy/runtime import, or a non-blocking side channel |
| `[( )]` | Datastore |
| `([ ])` | External actor |
| `{ }` | Decision point |

**Colour** — dark-theme first, using the dashboard's own status palette:

| Colour | Domain |
|:--|:--|
| 🔵 Blue `#3B82F6` | Perception and API |
| 🔴 Red `#EF4444` | Safety logic (rules, alerts) |
| 🟢 Emerald `#10B981` | Persistence |
| 🟡 Amber `#F59E0B` | Capture, composition, decision points |
| 🟣 Violet `#8B5CF6` | Client and interface |

## Accuracy notes

Two things the diagrams show that a generic architecture drawing would get wrong:

1. **`run_detection.py` is the composition root**, and it lives at the backend root — *not*
   inside `app/`. No module in `app/` imports `detection`, `tracking` or `rules`.

2. **`app.streaming` imports `run_detection` lazily**, which inverts layering on purpose. It
   reuses the existing pipeline instead of duplicating it, and the lazy import keeps the API
   importable without Torch or OpenCV installed.
