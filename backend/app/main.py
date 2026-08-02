"""FastAPI application entry point.

Instantiates the FastAPI application using values from :mod:`app.config`
and initializes application logging via :mod:`app.logger`.
"""

from typing import Any

from fastapi import FastAPI

from app.config import settings
from app.logger import logger

app: FastAPI = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

logger.info(f"Starting {settings.app_name} v{settings.app_version}")


@app.get("/")
def read_root() -> dict[str, Any]:
    """Report basic liveness and identification information.

    Returns:
        A JSON-serializable dictionary indicating that the service is
        running, along with the project name.
    """
    return {"status": "running", "project": "AI Warehouse Safety Inspector"}
