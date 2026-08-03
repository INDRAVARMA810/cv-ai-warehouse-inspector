"""API routers, one module per resource."""

from app.api.routers import alerts, health, system, tracks, violations

__all__ = ["alerts", "health", "system", "tracks", "violations"]
