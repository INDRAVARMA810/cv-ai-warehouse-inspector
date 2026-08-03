"""System event endpoints.

Exposes operational events emitted by the platform itself — pipeline
start/stop, camera loss, model load failures — which provide the
context needed to interpret why the system did or did not see
something. All data access goes through
:class:`~app.database.repositories.SystemRepository`.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    PaginationParams,
    SortParams,
    TimeRangeParams,
    get_system_repository,
)
from app.api.schemas import PageMeta, PaginatedResponse, SystemEventResponse
from app.database.repositories import Page, SystemRepository
from app.logger import logger

router = APIRouter(prefix="/system", tags=["system"])


def _to_response(page: Page) -> PaginatedResponse[SystemEventResponse]:
    """Convert a repository page into the API response model.

    Args:
        page: The repository page to convert.

    Returns:
        The paginated response.
    """
    return PaginatedResponse[SystemEventResponse](
        items=[SystemEventResponse.model_validate(row) for row in page.items],
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
    "/events",
    response_model=PaginatedResponse[SystemEventResponse],
    summary="List system events",
    description=(
        "Returns a paginated, filtered list of operational system events, "
        "newest first by default."
    ),
)
def list_system_events(
    pagination: PaginationParams = Depends(),
    sorting: SortParams = Depends(),
    time_range: TimeRangeParams = Depends(),
    repository: SystemRepository = Depends(get_system_repository),
    event_type: Optional[str] = Query(
        default=None, max_length=64, description="Match this event type."
    ),
    level: Optional[str] = Query(
        default=None, max_length=16, description="Match this event severity."
    ),
    source: Optional[str] = Query(
        default=None, max_length=128, description="Match the emitting component."
    ),
    search: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Case-insensitive substring matched against message and event type.",
    ),
) -> PaginatedResponse[SystemEventResponse]:
    """List system events matching the supplied filters.

    Args:
        pagination: Page number and size.
        sorting: Sort key and direction.
        time_range: Optional ``since``/``until`` bounds.
        repository: Injected system repository.
        event_type: Event type to match.
        level: Event severity to match.
        source: Emitting component to match.
        search: Free-text substring to match.

    Returns:
        The matching page of system events.
    """
    page = repository.search(
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sorting.sort_by,
        descending=sorting.descending,
        event_type=event_type,
        level=level,
        source=source,
        since=time_range.since,
        until=time_range.until,
        search=search,
    )

    logger.debug(f"Listed {len(page)} of {page.total} system event(s).")
    return _to_response(page)
