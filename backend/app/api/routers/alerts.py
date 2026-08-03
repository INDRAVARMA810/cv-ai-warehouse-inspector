"""Alert endpoints.

Exposes stored safety alerts for listing, retrieval and search. All
data access goes through :class:`~app.database.repositories.AlertRepository`;
this module imports no SQLAlchemy and builds no queries.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import (
    PaginationParams,
    SortParams,
    TimeRangeParams,
    get_alert_repository,
)
from app.api.schemas import (
    AlertAcknowledgeRequest,
    AlertCategorySchema,
    AlertLevelSchema,
    AlertResponse,
    AlertSearchRequest,
    AlertStatusSchema,
    PageMeta,
    PaginatedResponse,
    SortOrder,
)
from app.database.repositories import AlertRepository, Page
from app.logger import logger

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _to_response(page: Page) -> PaginatedResponse[AlertResponse]:
    """Convert a repository page into the API response model.

    Args:
        page: The repository page to convert.

    Returns:
        The paginated response.
    """
    return PaginatedResponse[AlertResponse](
        items=[AlertResponse.model_validate(row) for row in page.items],
        meta=PageMeta(
            total=page.total,
            page=page.page,
            page_size=page.page_size,
            pages=page.pages,
            has_next=page.has_next,
            has_previous=page.has_previous,
        ),
    )


@router.get(
    "",
    response_model=PaginatedResponse[AlertResponse],
    summary="List alerts",
    description=(
        "Returns a paginated, filtered list of safety alerts, newest first by "
        "default. Use `POST /alerts/search` when the criteria outgrow a query string."
    ),
)
def list_alerts(
    pagination: PaginationParams = Depends(),
    sorting: SortParams = Depends(),
    time_range: TimeRangeParams = Depends(),
    repository: AlertRepository = Depends(get_alert_repository),
    status_filter: Optional[AlertStatusSchema] = Query(
        default=None, alias="status", description="Match this lifecycle status."
    ),
    level: Optional[AlertLevelSchema] = Query(
        default=None, description="Match this exact urgency level."
    ),
    category: Optional[AlertCategorySchema] = Query(
        default=None, description="Match this hazard category."
    ),
    rule_name: Optional[str] = Query(
        default=None, max_length=128, description="Match this originating rule."
    ),
    track_id: Optional[int] = Query(
        default=None, ge=0, description="Match this track identity."
    ),
    acknowledged: Optional[bool] = Query(
        default=None, description="Match acknowledgement state."
    ),
    resolved: Optional[bool] = Query(default=None, description="Match resolution state."),
    search: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Case-insensitive substring matched against message and rule name.",
    ),
) -> PaginatedResponse[AlertResponse]:
    """List alerts matching the supplied filters.

    Args:
        pagination: Page number and size.
        sorting: Sort key and direction.
        time_range: Optional ``since``/``until`` bounds.
        repository: Injected alert repository.
        status_filter: Lifecycle status to match.
        level: Urgency level to match.
        category: Hazard category to match.
        rule_name: Originating rule to match.
        track_id: Track identity to match.
        acknowledged: Acknowledgement state to match.
        resolved: Resolution state to match.
        search: Free-text substring to match.

    Returns:
        The matching page of alerts.
    """
    page = repository.search(
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sorting.sort_by,
        descending=sorting.descending,
        status=status_filter.value if status_filter else None,
        level=level.value if level else None,
        category=category.value if category else None,
        rule_name=rule_name,
        track_id=track_id,
        acknowledged=acknowledged,
        resolved=resolved,
        since=time_range.since,
        until=time_range.until,
        search=search,
    )

    logger.debug(f"Listed {len(page)} of {page.total} alert(s).")
    return _to_response(page)


@router.post(
    "/search",
    response_model=PaginatedResponse[AlertResponse],
    summary="Search alerts",
    description=(
        "Returns a paginated, filtered list of alerts using a request body. "
        "Accepts the same criteria as `GET /alerts` plus multi-value level "
        "filtering, which does not express cleanly in a query string."
    ),
    status_code=status.HTTP_200_OK,
)
def search_alerts(
    request: AlertSearchRequest,
    repository: AlertRepository = Depends(get_alert_repository),
) -> PaginatedResponse[AlertResponse]:
    """Search alerts using a structured request body.

    Args:
        request: The search criteria.
        repository: Injected alert repository.

    Returns:
        The matching page of alerts.

    Raises:
        HTTPException: If ``since`` is later than ``until``.
    """
    if request.since and request.until and request.since > request.until:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="'since' must not be later than 'until'.",
        )

    page = repository.search(
        page=request.page,
        page_size=request.page_size,
        sort_by=request.sort_by,
        descending=request.order == SortOrder.DESC,
        status=request.status.value if request.status else None,
        level=request.level.value if request.level else None,
        levels=[level.value for level in request.levels] if request.levels else None,
        category=request.category.value if request.category else None,
        rule_name=request.rule_name,
        track_id=request.track_id,
        acknowledged=request.acknowledged,
        resolved=request.resolved,
        since=request.since,
        until=request.until,
        search=request.search,
    )

    logger.debug(f"Alert search matched {page.total} alert(s).")
    return _to_response(page)


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get an alert",
    description="Returns a single alert by its stable public identifier (UUID).",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No alert with that identifier."}},
)
def get_alert(
    alert_id: str = Path(
        ...,
        min_length=1,
        max_length=36,
        description="The alert's public identifier (UUID).",
    ),
    repository: AlertRepository = Depends(get_alert_repository),
) -> AlertResponse:
    """Fetch one alert by its public identifier.

    Args:
        alert_id: The alert's UUID.
        repository: Injected alert repository.

    Returns:
        The matching alert.

    Raises:
        HTTPException: With ``404`` if no such alert exists.
    """
    record = repository.get_by_alert_id(alert_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No alert found with id '{alert_id}'.",
        )

    return AlertResponse.model_validate(record)


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an alert",
    description=(
        "Marks an alert as seen by an operator. Acknowledging does not imply "
        "the hazard has cleared — use the resolve endpoint for that."
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "No alert with that identifier."}},
)
def acknowledge_alert(
    alert_id: str = Path(..., min_length=1, max_length=36, description="The alert's UUID."),
    body: AlertAcknowledgeRequest | None = None,
    repository: AlertRepository = Depends(get_alert_repository),
) -> AlertResponse:
    """Mark an alert as acknowledged.

    Args:
        alert_id: The alert's UUID.
        body: Optional payload naming the acknowledging operator.
        repository: Injected alert repository.

    Returns:
        The updated alert.

    Raises:
        HTTPException: With ``404`` if no such alert exists.
    """
    record = repository.acknowledge(alert_id, by=body.acknowledged_by if body else None)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No alert found with id '{alert_id}'.",
        )

    logger.info(f"Alert {alert_id} acknowledged via API.")
    return AlertResponse.model_validate(record)


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertResponse,
    summary="Resolve an alert",
    description="Marks an alert's underlying hazard as no longer present.",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No alert with that identifier."}},
)
def resolve_alert(
    alert_id: str = Path(..., min_length=1, max_length=36, description="The alert's UUID."),
    repository: AlertRepository = Depends(get_alert_repository),
) -> AlertResponse:
    """Mark an alert as resolved.

    Args:
        alert_id: The alert's UUID.
        repository: Injected alert repository.

    Returns:
        The updated alert.

    Raises:
        HTTPException: With ``404`` if no such alert exists.
    """
    record = repository.resolve(alert_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No alert found with id '{alert_id}'.",
        )

    logger.info(f"Alert {alert_id} resolved via API.")
    return AlertResponse.model_validate(record)
