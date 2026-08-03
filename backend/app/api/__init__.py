"""REST API layer.

Exposes the platform over HTTP using FastAPI. The layer is arranged so
that routers depend only on repositories:

* :mod:`app.api.schemas` defines the public request/response contract.
* :mod:`app.api.dependencies` injects request-scoped repositories.
* :mod:`app.api.routers` holds one router per resource.
* :mod:`app.api.exceptions` converts every failure into one envelope.

No router imports SQLAlchemy or builds a query — all persistence goes
through :mod:`app.database.repositories`.
"""

from fastapi import APIRouter

from app.api.exceptions import register_exception_handlers
from app.api.routers import alerts, health, system, tracks, violations

#: Prefix applied to every versioned endpoint. Versioning the path from
#: the outset means a future breaking change can ship alongside the
#: current contract instead of replacing it.
API_PREFIX = "/api/v1"

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(alerts.router)
api_router.include_router(violations.router)
api_router.include_router(tracks.router)
api_router.include_router(system.router)

__all__ = ["api_router", "API_PREFIX", "register_exception_handlers"]
