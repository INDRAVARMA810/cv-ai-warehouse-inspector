"""Track endpoints.

Exposes the recorded lifetimes of tracked objects. All data access goes
through :class:`~app.database.repositories.TrackRepository`.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    PaginationParams,
    SortParams,
    TimeRangeParams,
    get_track_repository,
)
from app.api.schemas import PageMeta, PaginatedResponse, TrackResponse
from app.database.repositories import Page, TrackRepository
from app.logger import logger

router = APIRouter(prefix="/tracks", tags=["tracks"])


def _to_response(page: Page) -> PaginatedResponse[TrackResponse]:
    """Convert a repository page into the API response model.

    Args:
        page: The repository page to convert.

    Returns:
        The paginated response.
    """
    return PaginatedResponse[TrackResponse](
        items=[TrackResponse.model_validate(row) for row in page.items],
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
    response_model=PaginatedResponse[TrackResponse],
    summary="List tracked objects",
    description=(
        "Returns a paginated, filtered list of tracked-object lifetimes, most "
        "recently first-seen by default. Each row summarizes one identity's "
        "whole appearance rather than a single frame."
    ),
)
def list_tracks(
    pagination: PaginationParams = Depends(),
    sorting: SortParams = Depends(),
    time_range: TimeRangeParams = Depends(),
    repository: TrackRepository = Depends(get_track_repository),
    track_id: Optional[int] = Query(
        default=None, ge=0, description="Match this track identity."
    ),
    class_name: Optional[str] = Query(
        default=None, max_length=64, description="Match this object class."
    ),
    min_observations: Optional[int] = Query(
        default=None,
        ge=1,
        description="Only tracks observed in at least this many frames.",
    ),
    search: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Case-insensitive substring matched against the class name.",
    ),
) -> PaginatedResponse[TrackResponse]:
    """List tracked objects matching the supplied filters.

    Args:
        pagination: Page number and size.
        sorting: Sort key and direction.
        time_range: Optional ``since``/``until`` bounds on first sighting.
        repository: Injected track repository.
        track_id: Track identity to match.
        class_name: Object class to match.
        min_observations: Minimum observation count.
        search: Free-text substring to match.

    Returns:
        The matching page of tracks.
    """
    page = repository.search(
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sorting.sort_by,
        descending=sorting.descending,
        track_id=track_id,
        class_name=class_name,
        min_observations=min_observations,
        since=time_range.since,
        until=time_range.until,
        search=search,
    )

    logger.debug(f"Listed {len(page)} of {page.total} track(s).")
    return _to_response(page)
