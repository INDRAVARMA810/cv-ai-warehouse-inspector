"""Health check endpoint.

Reports whether the service and its dependencies are usable. Kept
deliberately cheap and non-throwing: a health probe must return a
verdict even when everything behind it is broken, so an unreachable
database yields ``degraded`` rather than an error.
"""

from fastapi import APIRouter, Response, status

from app.api.schemas import ComponentHealth, HealthResponse
from app.config import settings
from app.database.database import get_database
from app.logger import logger

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health",
    description=(
        "Reports service and dependency health. Returns HTTP 200 when every "
        "component is healthy and HTTP 503 when any component is degraded, so "
        "load balancers and orchestrators can act on the status code alone."
    ),
    responses={
        status.HTTP_200_OK: {"description": "All components healthy."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "One or more components degraded."},
    },
)
def get_health(response: Response) -> HealthResponse:
    """Report the health of the service and its dependencies.

    Args:
        response: The outgoing response, whose status code is set to
            ``503`` when any component is unhealthy.

    Returns:
        The health report.
    """
    database_healthy = get_database().check_connection()

    components = [
        ComponentHealth(
            name="database",
            healthy=database_healthy,
            detail=None if database_healthy else "Connection check failed.",
        ),
        ComponentHealth(name="api", healthy=True, detail=None),
    ]

    healthy = all(component.healthy for component in components)

    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        logger.warning("Health check reported a degraded service.")

    return HealthResponse(
        status="ok" if healthy else "degraded",
        application=settings.app_name,
        version=settings.app_version,
        components=components,
    )
