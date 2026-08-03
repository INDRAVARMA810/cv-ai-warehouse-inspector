"""API routers, one module per resource."""

from app.api.routers import alerts, health, stream, system, tracks, violations

__all__ = ["alerts", "health", "stream", "system", "tracks", "violations"]
