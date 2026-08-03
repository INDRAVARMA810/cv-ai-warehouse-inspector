"""FastAPI dependency providers.

Supplies request-scoped database sessions, repository instances, and
reusable query-parameter groups.

Routers depend on **repositories**, never on a session or the ORM
directly. The session exists here only long enough to construct them,
which keeps the "all database access goes through repositories" rule
enforceable by inspection: no router imports SQLAlchemy at all.
"""

from datetime import datetime
from typing import Iterator, Optional

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.repositories import MAX_PAGE_SIZE as REPOSITORY_MAX_PAGE_SIZE
from app.database.repositories import (
    AlertRepository,
    SystemRepository,
    TrackRepository,
    ViolationRepository,
)
from app.database.session import get_session_manager
from app.logger import logger

#: Largest page a client may request. Sourced from the repository layer
#: so the documented API limit cannot drift from the enforced one.
MAX_PAGE_SIZE = REPOSITORY_MAX_PAGE_SIZE


def get_session() -> Iterator[Session]:
    """Provide a request-scoped database session.

    Commits when the request handler returns normally and rolls back if
    it raises, so a failed request never leaves a partial write behind.
    The session is always closed.

    Yields:
        A session for the lifetime of the request.
    """
    session = get_session_manager().create_session()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.debug("Request-scoped session rolled back.")
        raise
    finally:
        session.close()


def get_alert_repository(
    session: Session = Depends(get_session),
) -> AlertRepository:
    """Provide an :class:`AlertRepository` bound to the request session.

    Args:
        session: The request-scoped session.

    Returns:
        The repository.
    """
    return AlertRepository(session)


def get_violation_repository(
    session: Session = Depends(get_session),
) -> ViolationRepository:
    """Provide a :class:`ViolationRepository` bound to the request session.

    Args:
        session: The request-scoped session.

    Returns:
        The repository.
    """
    return ViolationRepository(session)


def get_track_repository(
    session: Session = Depends(get_session),
) -> TrackRepository:
    """Provide a :class:`TrackRepository` bound to the request session.

    Args:
        session: The request-scoped session.

    Returns:
        The repository.
    """
    return TrackRepository(session)


def get_system_repository(
    session: Session = Depends(get_session),
) -> SystemRepository:
    """Provide a :class:`SystemRepository` bound to the request session.

    Args:
        session: The request-scoped session.

    Returns:
        The repository.
    """
    return SystemRepository(session)


class PaginationParams:
    """Shared ``page`` / ``page_size`` query parameters.

    Attributes:
        page: 1-based page number.
        page_size: Rows per page.
    """

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="1-based page number."),
        page_size: int = Query(
            default=50,
            ge=1,
            le=MAX_PAGE_SIZE,
            description=f"Rows per page (maximum {MAX_PAGE_SIZE}).",
        ),
    ) -> None:
        """Capture the pagination parameters.

        Args:
            page: 1-based page number.
            page_size: Rows per page.
        """
        self.page = page
        self.page_size = page_size


class SortParams:
    """Shared ``sort_by`` / ``order`` query parameters.

    Sort keys are validated by the repository against its allowlist;
    an unsupported key falls back to that repository's default ordering
    rather than failing the request.

    Attributes:
        sort_by: Requested sort key, if any.
        descending: Whether to sort descending.
    """

    def __init__(
        self,
        sort_by: Optional[str] = Query(
            default=None,
            max_length=64,
            description="Field to sort by. Unsupported values use the default ordering.",
        ),
        order: str = Query(
            default="desc",
            pattern="^(asc|desc)$",
            description="Sort direction: 'asc' or 'desc'.",
        ),
    ) -> None:
        """Capture the sorting parameters.

        Args:
            sort_by: Requested sort key.
            order: Sort direction.
        """
        self.sort_by = sort_by
        self.descending = order.lower() != "asc"


class TimeRangeParams:
    """Shared ``since`` / ``until`` query parameters.

    Attributes:
        since: Lower bound, inclusive.
        until: Upper bound, inclusive.
    """

    def __init__(
        self,
        since: Optional[datetime] = Query(
            default=None, description="Only records at or after this timestamp (ISO 8601)."
        ),
        until: Optional[datetime] = Query(
            default=None, description="Only records at or before this timestamp (ISO 8601)."
        ),
    ) -> None:
        """Capture and validate the time range.

        Args:
            since: Lower bound.
            until: Upper bound.

        Raises:
            HTTPException: If ``since`` is later than ``until``, which
                would silently return nothing.
        """
        if since is not None and until is not None and since > until:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"'since' ({since.isoformat()}) must not be later than 'until' ({until.isoformat()}).",
            )

        self.since = since
        self.until = until
