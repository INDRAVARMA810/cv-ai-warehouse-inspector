"""FastAPI application entry point.

Instantiates the application using values from :mod:`app.config`,
initializes logging via :mod:`app.logger`, registers the global
exception handlers, and mounts the versioned API router.

Run from the ``backend/`` directory with::

    uvicorn app.main:app --reload

Interactive documentation is served at ``/docs`` (Swagger UI) and
``/redoc``, with the raw schema at ``/openapi.json``.
"""

from typing import Any

from fastapi import FastAPI

from app.api import API_PREFIX, api_router, register_exception_handlers
from app.config import settings
from app.logger import logger

DESCRIPTION = """
REST API for the **AI Warehouse Safety Inspector**.

Exposes the safety alerts, rule violations, tracked objects and system
events recorded by the detection pipeline.

* **Pagination** — every list endpoint accepts `page` and `page_size`
  and returns a `meta` block describing the result set.
* **Filtering** — resource-specific query parameters, plus `since` and
  `until` time bounds.
* **Sorting** — `sort_by` with `order=asc|desc`. Unsupported sort keys
  fall back to the endpoint's default ordering.
* **Searching** — `search` performs a case-insensitive substring match
  across each resource's text fields.

Authentication is not yet implemented; every endpoint is currently open.
"""

app: FastAPI = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "AI Warehouse Safety Inspector"},
    license_info={"name": "MIT"},
)

register_exception_handlers(app)
app.include_router(api_router, prefix=API_PREFIX)

logger.info(
    f"Starting {settings.app_name} v{settings.app_version}; "
    f"API mounted at {API_PREFIX}"
)


@app.get("/", tags=["root"], summary="Service banner")
def read_root() -> dict[str, Any]:
    """Report basic liveness and identification information.

    Returns:
        A JSON-serializable dictionary indicating that the service is
        running, along with the project name and where to find the API.
    """
    return {
        "status": "running",
        "project": "AI Warehouse Safety Inspector",
        "version": settings.app_version,
        "api": API_PREFIX,
        "docs": "/docs",
    }
