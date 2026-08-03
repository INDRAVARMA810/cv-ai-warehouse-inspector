"""Violation endpoints.

Exposes the individual rule violations that underlie alerts. All data
access goes through
:class:`~app.database.repositories.ViolationRepository`.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    PaginationParams,
    SortParams,
    TimeRangeParams,
    get_violation_repository,
)
from app.api.schemas import (
    AlertLevelSchema,
    PageMeta,
    PaginatedResponse,
    ViolationResponse,
)
from app.database.repositories import Page, ViolationRepository
from app.logger import logger

router = APIRouter(prefix="/violations", tags=["violations"])


def _to_response(page: Page) -> PaginatedResponse[ViolationResponse]:
    """Convert a repository page into the API response model.

    Args:
        page: The repository page to convert.

    Returns:
        The paginated response.
    """
    return PaginatedResponse[ViolationResponse](
        items=[ViolationResponse.model_validate(row) for row in page.items],
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
    response_model=PaginatedResponse[ViolationResponse],
    summary="List violations",
    description=(
        "Returns a paginated, filtered list of rule violations, newest first "
        "by default. Filter by `alert_id` to retrieve the evidence behind a "
        "specific alert."
    ),
)
def list_violations(
    pagination: PaginationParams = Depends(),
    sorting: SortParams = Depends(),
    time_range: TimeRangeParams = Depends(),
    repository: ViolationRepository = Depends(get_violation_repository),
    rule_name: Optional[str] = Query(
        default=None, max_length=128, description="Match this originating rule."
    ),
    severity: Optional[AlertLevelSchema] = Query(
        default=None, description="Match this severity."
    ),
    track_id: Optional[int] = Query(
        default=None, ge=0, description="Match this track identity."
    ),
    alert_id: Optional[str] = Query(
        default=None,
        max_length=36,
        description="Only violations belonging to this alert.",
    ),
    search: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Case-insensitive substring matched against description and rule name.",
    ),
) -> PaginatedResponse[ViolationResponse]:
    """List violations matching the supplied filters.

    Args:
        pagination: Page number and size.
        sorting: Sort key and direction.
        time_range: Optional ``since``/``until`` bounds.
        repository: Injected violation repository.
        rule_name: Originating rule to match.
        severity: Severity to match.
        track_id: Track identity to match.
        alert_id: Owning alert to match.
        search: Free-text substring to match.

    Returns:
        The matching page of violations.
    """
    page = repository.search(
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sorting.sort_by,
        descending=sorting.descending,
        rule_name=rule_name,
        severity=severity.value if severity else None,
        track_id=track_id,
        alert_id=alert_id,
        since=time_range.since,
        until=time_range.until,
        search=search,
    )

    logger.debug(f"Listed {len(page)} of {page.total} violation(s).")
    return _to_response(page)
