"""Repository layer — the only place that talks to the database.

Every read and write goes through a repository. Business logic never
builds a query, so the storage backend can change without the domain
layer noticing, and the data-access surface stays small enough to
review.

Repositories are handed a :class:`~sqlalchemy.orm.Session` rather than
creating one. That keeps the unit-of-work boundary with the caller —
several repositories can participate in a single transaction, and
:func:`app.database.session.session_scope` decides when to commit.
Repositories *flush* (so generated IDs are available) but never commit.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
)

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session

from app.database.models import (
    AlertRecord,
    Base,
    SystemEvent,
    TrackRecord,
    ViolationRecord,
    epoch_to_datetime,
    utcnow,
)
from app.logger import logger

ModelT = TypeVar("ModelT", bound=Base)

#: Upper bound on ``page_size``, so a caller cannot accidentally ask
#: for the entire table in one query.
MAX_PAGE_SIZE = 500


@dataclass
class Page(Generic[ModelT]):
    """One page of query results.

    Attributes:
        items: The rows on this page.
        total: Total rows matching the query, ignoring pagination.
        page: 1-based page number.
        page_size: Rows requested per page.
    """

    items: List[ModelT]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        """Total number of pages available."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size

    @property
    def has_next(self) -> bool:
        """Whether a further page exists."""
        return self.page < self.pages

    @property
    def has_previous(self) -> bool:
        """Whether an earlier page exists."""
        return self.page > 1

    def __len__(self) -> int:
        """Return the number of items on this page."""
        return len(self.items)

    def to_dict(self) -> Dict[str, Any]:
        """Return pagination metadata (without the rows themselves)."""
        return {
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
            "count": len(self.items),
        }


def _box_to_json(
    box: Optional[Sequence[float]],
) -> Optional[Dict[str, float]]:
    """Convert an ``(x1, y1, x2, y2)`` box into a JSON-friendly mapping.

    Args:
        box: The box coordinates, or ``None``.

    Returns:
        A ``{"x1": ..., "y1": ..., "x2": ..., "y2": ...}`` mapping, or
        ``None``.
    """
    if box is None:
        return None

    try:
        x1, y1, x2, y2 = (float(value) for value in box)
    except (TypeError, ValueError):
        return None

    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


class BaseRepository(Generic[ModelT]):
    """Generic CRUD, filtering and pagination for one model.

    Attributes:
        session: The session this repository operates within.
        model: The mapped class this repository manages.
        sortable_fields: Public sort keys mapped to model attribute
            names. Sorting is restricted to this allowlist so callers
            can pass a plain string without the data layer accepting an
            arbitrary column name.
    """

    model: Type[ModelT]
    sortable_fields: Dict[str, str] = {}

    def __init__(self, session: Session) -> None:
        """Bind the repository to a session.

        Args:
            session: The session providing the unit of work.
        """
        self.session = session

    # ---------------------------------------------------------------
    # Create
    # ---------------------------------------------------------------

    def create(self, **values: Any) -> ModelT:
        """Insert a new row.

        Args:
            **values: Column values for the new row.

        Returns:
            The persisted instance, flushed so its primary key is set.
        """
        instance = self.model(**values)
        return self.add(instance)

    def add(self, instance: ModelT) -> ModelT:
        """Add an existing instance to the session.

        Args:
            instance: The instance to persist.

        Returns:
            The same instance, flushed so its primary key is set.
        """
        self.session.add(instance)
        self.session.flush()
        return instance

    def bulk_create(self, rows: Sequence[Dict[str, Any]]) -> List[ModelT]:
        """Insert many rows in one flush.

        Args:
            rows: One mapping of column values per row.

        Returns:
            The persisted instances.
        """
        instances = [self.model(**row) for row in rows]

        if not instances:
            return []

        self.session.add_all(instances)
        self.session.flush()
        logger.debug(f"Inserted {len(instances)} {self.model.__name__} row(s).")
        return instances

    # ---------------------------------------------------------------
    # Read
    # ---------------------------------------------------------------

    def get(self, row_id: int) -> Optional[ModelT]:
        """Fetch a row by primary key.

        Args:
            row_id: The primary key value.

        Returns:
            The row, or ``None`` if it does not exist.
        """
        return self.session.get(self.model, row_id)

    def first(self, **filters: Any) -> Optional[ModelT]:
        """Fetch the first row matching equality filters.

        Args:
            **filters: Column-value pairs to match exactly.

        Returns:
            The first matching row, or ``None``.
        """
        statement = self._apply_equality_filters(select(self.model), filters)
        return self.session.execute(statement.limit(1)).scalars().first()

    def list(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: Optional[Any] = None,
        descending: bool = True,
        **filters: Any,
    ) -> List[ModelT]:
        """Fetch rows matching equality filters.

        Args:
            limit: Maximum rows to return.
            offset: Rows to skip.
            order_by: Column to order by. Defaults to the primary key.
            descending: Whether to sort descending.
            **filters: Column-value pairs to match exactly.

        Returns:
            The matching rows.
        """
        statement = self._apply_equality_filters(select(self.model), filters)
        statement = self._apply_ordering(statement, order_by, descending)

        if offset:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)

        return list(self.session.execute(statement).scalars().all())

    def count(self, **filters: Any) -> int:
        """Count rows matching equality filters.

        Args:
            **filters: Column-value pairs to match exactly.

        Returns:
            The number of matching rows.
        """
        statement = self._apply_equality_filters(
            select(func.count()).select_from(self.model), filters
        )
        return int(self.session.execute(statement).scalar_one())

    def exists(self, **filters: Any) -> bool:
        """Return whether any row matches the given filters.

        Args:
            **filters: Column-value pairs to match exactly.

        Returns:
            ``True`` if at least one row matches.
        """
        return self.count(**filters) > 0

    def paginate(
        self,
        page: int = 1,
        page_size: int = 50,
        order_by: Optional[Any] = None,
        descending: bool = True,
        statement: Optional[Select] = None,
        **filters: Any,
    ) -> Page[ModelT]:
        """Fetch one page of results, with a total count.

        Args:
            page: 1-based page number. Values below 1 are clamped.
            page_size: Rows per page, clamped to
                :data:`MAX_PAGE_SIZE`.
            order_by: Column to order by. Defaults to the primary key.
            descending: Whether to sort descending.
            statement: A pre-built ``SELECT`` to paginate. When given,
                ``filters`` are applied on top of it. This is how
                subclasses expose rich filtering without duplicating
                pagination logic.
            **filters: Column-value pairs to match exactly.

        Returns:
            The requested :class:`Page`.
        """
        page = max(1, page)
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))

        base = select(self.model) if statement is None else statement
        base = self._apply_equality_filters(base, filters)

        # Count against the same criteria, with ordering stripped —
        # ORDER BY is meaningless in a COUNT and costs time.
        count_statement = select(func.count()).select_from(
            base.order_by(None).subquery()
        )
        total = int(self.session.execute(count_statement).scalar_one())

        ordered = self._apply_ordering(base, order_by, descending)
        rows = (
            self.session.execute(
                ordered.offset((page - 1) * page_size).limit(page_size)
            )
            .scalars()
            .all()
        )

        return Page(items=list(rows), total=total, page=page, page_size=page_size)

    # ---------------------------------------------------------------
    # Update / Delete
    # ---------------------------------------------------------------

    def update(self, row_id: int, **values: Any) -> Optional[ModelT]:
        """Update a row by primary key.

        Args:
            row_id: The primary key value.
            **values: Column values to set. Unknown column names are
                ignored, so a caller cannot silently create attributes.

        Returns:
            The updated row, or ``None`` if it does not exist.
        """
        instance = self.get(row_id)

        if instance is None:
            logger.warning(
                f"Cannot update {self.model.__name__} id={row_id}: not found."
            )
            return None

        return self.update_instance(instance, **values)

    def update_instance(self, instance: ModelT, **values: Any) -> ModelT:
        """Apply column values to an already-loaded instance.

        Args:
            instance: The row to update.
            **values: Column values to set. Unknown names are ignored.

        Returns:
            The updated instance.
        """
        for key, value in values.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
            else:
                logger.warning(
                    f"Ignoring unknown field '{key}' for {self.model.__name__}."
                )

        self.session.flush()
        return instance

    def delete(self, row_id: int) -> bool:
        """Delete a row by primary key.

        Args:
            row_id: The primary key value.

        Returns:
            ``True`` if a row was deleted, ``False`` if none existed.
        """
        instance = self.get(row_id)

        if instance is None:
            logger.warning(
                f"Cannot delete {self.model.__name__} id={row_id}: not found."
            )
            return False

        self.session.delete(instance)
        self.session.flush()
        return True

    def delete_where(self, **filters: Any) -> int:
        """Delete every row matching equality filters.

        Args:
            **filters: Column-value pairs to match exactly.

        Returns:
            The number of rows deleted.
        """
        statement = delete(self.model)

        for field, value in filters.items():
            column = getattr(self.model, field, None)
            if column is None:
                logger.warning(
                    f"Ignoring unknown filter '{field}' for {self.model.__name__}."
                )
                continue
            statement = statement.where(column == value)

        result = self.session.execute(statement)
        self.session.flush()

        deleted = int(result.rowcount or 0)
        if deleted:
            logger.debug(f"Deleted {deleted} {self.model.__name__} row(s).")

        return deleted

    # ---------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------

    def _apply_equality_filters(
        self, statement: Select, filters: Dict[str, Any]
    ) -> Select:
        """Apply ``column == value`` filters to a statement.

        Args:
            statement: The statement to extend.
            filters: Column-value pairs. ``None`` values are skipped so
                callers can pass optional arguments straight through.

        Returns:
            The filtered statement.
        """
        for field, value in filters.items():
            if value is None:
                continue

            column = getattr(self.model, field, None)
            if column is None:
                logger.warning(
                    f"Ignoring unknown filter '{field}' for {self.model.__name__}."
                )
                continue

            statement = statement.where(column == value)

        return statement

    def resolve_sort(self, sort_by: Optional[str]) -> Optional[Any]:
        """Translate a public sort key into a model column.

        Args:
            sort_by: The requested sort key, or ``None``.

        Returns:
            The matching column, or ``None`` to fall back to the
            repository's default ordering. Unknown keys are rejected
            rather than passed through, so a caller cannot sort by an
            arbitrary attribute.
        """
        if not sort_by:
            return None

        attribute = self.sortable_fields.get(sort_by)

        if attribute is None:
            logger.warning(
                f"Ignoring unsupported sort key '{sort_by}' for "
                f"{self.model.__name__}; using default ordering."
            )
            return None

        return getattr(self.model, attribute, None)

    def _apply_ordering(
        self, statement: Select, order_by: Optional[Any], descending: bool
    ) -> Select:
        """Apply an ORDER BY clause, defaulting to the primary key.

        Args:
            statement: The statement to extend.
            order_by: Column to order by, or ``None`` for the default.
            descending: Whether to sort descending.

        Returns:
            The ordered statement.
        """
        column = order_by if order_by is not None else self.model.id
        return statement.order_by(column.desc() if descending else column.asc())


class AlertRepository(BaseRepository[AlertRecord]):
    """Persistence for safety alerts."""

    model = AlertRecord
    sortable_fields = {
        "occurred_at": "occurred_at",
        "level": "level",
        "status": "status",
        "rule_name": "rule_name",
        "category": "category",
        "track_id": "track_id",
        "occurrence_count": "occurrence_count",
        "created_at": "created_at",
    }

    @staticmethod
    def to_values(alert: Any) -> Dict[str, Any]:
        """Map a domain alert onto column values.

        Accepts any object with the shape of
        :class:`app.alerts.alert.Alert`, keeping this layer decoupled
        from the alert package.

        Args:
            alert: The domain alert to map.

        Returns:
            Column values suitable for :meth:`create` or
            :meth:`update_instance`.
        """
        return {
            "alert_id": str(alert.alert_id),
            "occurred_at": epoch_to_datetime(alert.timestamp),
            "rule_name": str(alert.rule_name),
            "level": str(alert.level),
            "initial_level": str(alert.initial_level) if alert.initial_level else None,
            "category": alert.category.value
            if hasattr(alert.category, "value")
            else str(alert.category),
            "status": alert.status.value
            if hasattr(alert.status, "value")
            else str(alert.status),
            "message": str(alert.message),
            "track_id": alert.track_id,
            "frame_number": alert.frame_number,
            "bounding_box": _box_to_json(alert.bounding_box),
            "occurrence_count": int(alert.occurrence_count),
            "first_seen": epoch_to_datetime(alert.first_seen),
            "last_seen": epoch_to_datetime(alert.last_seen),
            "acknowledged": bool(alert.acknowledged),
            "acknowledged_at": epoch_to_datetime(alert.acknowledged_at),
            "acknowledged_by": alert.acknowledged_by,
            "resolved": bool(alert.resolved),
            "resolved_at": epoch_to_datetime(alert.resolved_at),
            "was_escalated": bool(alert.was_escalated),
            "extra_metadata": dict(alert.metadata) if alert.metadata else None,
        }

    def get_by_alert_id(self, alert_id: str) -> Optional[AlertRecord]:
        """Fetch an alert by its domain identifier.

        Args:
            alert_id: The domain alert ID (UUID).

        Returns:
            The alert record, or ``None``.
        """
        return self.first(alert_id=alert_id)

    def save_domain(self, alert: Any) -> AlertRecord:
        """Insert or update the row for a domain alert.

        Alerts are deduplicated upstream, so the same ``alert_id``
        recurs as an incident evolves. This upserts rather than
        inserting duplicates.

        Args:
            alert: The domain alert to persist.

        Returns:
            The persisted record.
        """
        values = self.to_values(alert)
        existing = self.get_by_alert_id(values["alert_id"])

        if existing is not None:
            return self.update_instance(existing, **values)

        return self.create(**values)

    def save_many_domain(self, alerts: Sequence[Any]) -> List[AlertRecord]:
        """Persist several domain alerts.

        Args:
            alerts: The domain alerts to persist.

        Returns:
            The persisted records.
        """
        return [self.save_domain(alert) for alert in alerts]

    def build_query(
        self,
        status: Optional[str] = None,
        level: Optional[str] = None,
        levels: Optional[Sequence[str]] = None,
        category: Optional[str] = None,
        rule_name: Optional[str] = None,
        track_id: Optional[int] = None,
        acknowledged: Optional[bool] = None,
        resolved: Optional[bool] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> Select:
        """Build a filtered ``SELECT`` for alerts.

        Exposed so callers can hand the result to :meth:`paginate`
        without this layer leaking query construction upward.

        Args:
            status: Match this lifecycle status.
            level: Match this exact urgency level.
            levels: Match any of these urgency levels.
            category: Match this category.
            rule_name: Match this originating rule.
            track_id: Match this track identity.
            acknowledged: Match acknowledgement state.
            resolved: Match resolution state.
            since: Only alerts at or after this time.
            until: Only alerts at or before this time.
            search: Case-insensitive substring matched against the
                message and rule name.

        Returns:
            The filtered statement.
        """
        statement = select(AlertRecord)

        if status is not None:
            statement = statement.where(AlertRecord.status == status)
        if level is not None:
            statement = statement.where(AlertRecord.level == level)
        if levels:
            statement = statement.where(AlertRecord.level.in_(list(levels)))
        if category is not None:
            statement = statement.where(AlertRecord.category == category)
        if rule_name is not None:
            statement = statement.where(AlertRecord.rule_name == rule_name)
        if track_id is not None:
            statement = statement.where(AlertRecord.track_id == track_id)
        if acknowledged is not None:
            statement = statement.where(AlertRecord.acknowledged.is_(acknowledged))
        if resolved is not None:
            statement = statement.where(AlertRecord.resolved.is_(resolved))
        if since is not None:
            statement = statement.where(AlertRecord.occurred_at >= since)
        if until is not None:
            statement = statement.where(AlertRecord.occurred_at <= until)

        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                AlertRecord.message.ilike(pattern)
                | AlertRecord.rule_name.ilike(pattern)
            )

        return statement

    def search(
        self,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        descending: bool = True,
        **criteria: Any,
    ) -> Page[AlertRecord]:
        """Return a filtered, paginated page of alerts.

        Args:
            page: 1-based page number.
            page_size: Rows per page.
            sort_by: Sort key from :attr:`sortable_fields`. Defaults to
                the time the alert occurred.
            descending: Whether to sort descending.
            **criteria: Any argument accepted by :meth:`build_query`.

        Returns:
            The matching page.
        """
        return self.paginate(
            page=page,
            page_size=page_size,
            order_by=self.resolve_sort(sort_by) or AlertRecord.occurred_at,
            descending=descending,
            statement=self.build_query(**criteria),
        )

    def active(self, limit: int = 100) -> List[AlertRecord]:
        """Return alerts still awaiting attention, most recent first.

        Args:
            limit: Maximum rows to return.

        Returns:
            The active alerts.
        """
        return self.list(
            limit=limit, order_by=AlertRecord.occurred_at, status="active"
        )

    def acknowledge(
        self, alert_id: str, by: Optional[str] = None
    ) -> Optional[AlertRecord]:
        """Mark a stored alert as acknowledged.

        Args:
            alert_id: The domain alert ID.
            by: Identifier of the acknowledging operator.

        Returns:
            The updated record, or ``None`` if it does not exist.
        """
        record = self.get_by_alert_id(alert_id)

        if record is None:
            logger.warning(f"Cannot acknowledge unknown alert '{alert_id}'.")
            return None

        return self.update_instance(
            record,
            status="acknowledged",
            acknowledged=True,
            acknowledged_at=utcnow(),
            acknowledged_by=by,
        )

    def resolve(self, alert_id: str) -> Optional[AlertRecord]:
        """Mark a stored alert as resolved.

        Args:
            alert_id: The domain alert ID.

        Returns:
            The updated record, or ``None`` if it does not exist.
        """
        record = self.get_by_alert_id(alert_id)

        if record is None:
            logger.warning(f"Cannot resolve unknown alert '{alert_id}'.")
            return None

        return self.update_instance(
            record, status="resolved", resolved=True, resolved_at=utcnow()
        )

    def count_by_level(self) -> Dict[str, int]:
        """Return the number of alerts at each urgency level.

        Returns:
            A ``{level: count}`` mapping.
        """
        rows = self.session.execute(
            select(AlertRecord.level, func.count()).group_by(AlertRecord.level)
        ).all()
        return {level: int(count) for level, count in rows}

    def count_by_status(self) -> Dict[str, int]:
        """Return the number of alerts in each lifecycle status.

        Returns:
            A ``{status: count}`` mapping.
        """
        rows = self.session.execute(
            select(AlertRecord.status, func.count()).group_by(AlertRecord.status)
        ).all()
        return {status: int(count) for status, count in rows}

    def purge_before(self, cutoff: datetime) -> int:
        """Delete alerts that occurred before a cutoff.

        Args:
            cutoff: Alerts strictly older than this are removed, along
                with their violations via cascade.

        Returns:
            The number of alerts deleted.
        """
        stale = list(
            self.session.execute(
                select(AlertRecord).where(AlertRecord.occurred_at < cutoff)
            )
            .scalars()
            .all()
        )

        for record in stale:
            self.session.delete(record)

        self.session.flush()

        if stale:
            logger.info(f"Purged {len(stale)} alert(s) older than {cutoff}.")

        return len(stale)


class ViolationRepository(BaseRepository[ViolationRecord]):
    """Persistence for individual rule violations."""

    model = ViolationRecord
    sortable_fields = {
        "occurred_at": "occurred_at",
        "severity": "severity",
        "rule_name": "rule_name",
        "track_id": "track_id",
        "created_at": "created_at",
    }

    @staticmethod
    def to_values(violation: Any, alert_id: Optional[str] = None) -> Dict[str, Any]:
        """Map a domain violation onto column values.

        Args:
            violation: An object shaped like
                :class:`app.rules.rule_result.RuleViolation`.
            alert_id: The owning alert's domain ID, if any.

        Returns:
            Column values for the new row.
        """
        return {
            "alert_id": alert_id,
            "occurred_at": epoch_to_datetime(violation.timestamp),
            "rule_name": str(violation.rule_name),
            "severity": str(violation.severity),
            "description": str(violation.description),
            "track_id": violation.track_id,
            "frame_number": violation.frame_number,
            "bounding_box": _box_to_json(violation.bounding_box),
            "extra_metadata": dict(violation.metadata) if violation.metadata else None,
        }

    def save_domain(
        self, violation: Any, alert_id: Optional[str] = None
    ) -> ViolationRecord:
        """Persist one domain violation.

        Args:
            violation: The violation to persist.
            alert_id: The owning alert's domain ID, if any.

        Returns:
            The persisted record.
        """
        return self.create(**self.to_values(violation, alert_id=alert_id))

    def save_many_domain(
        self, violations: Sequence[Any], alert_id: Optional[str] = None
    ) -> List[ViolationRecord]:
        """Persist several domain violations in one flush.

        Args:
            violations: The violations to persist.
            alert_id: The owning alert's domain ID, if any.

        Returns:
            The persisted records.
        """
        return self.bulk_create(
            [self.to_values(v, alert_id=alert_id) for v in violations]
        )

    def build_query(
        self,
        rule_name: Optional[str] = None,
        severity: Optional[str] = None,
        track_id: Optional[int] = None,
        alert_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> Select:
        """Build a filtered ``SELECT`` for violations.

        Args:
            rule_name: Match this originating rule.
            severity: Match this severity.
            track_id: Match this track identity.
            alert_id: Match violations belonging to this alert.
            since: Only violations at or after this time.
            until: Only violations at or before this time.
            search: Case-insensitive substring matched against the
                description and rule name.

        Returns:
            The filtered statement.
        """
        statement = select(ViolationRecord)

        if rule_name is not None:
            statement = statement.where(ViolationRecord.rule_name == rule_name)
        if severity is not None:
            statement = statement.where(ViolationRecord.severity == severity)
        if track_id is not None:
            statement = statement.where(ViolationRecord.track_id == track_id)
        if alert_id is not None:
            statement = statement.where(ViolationRecord.alert_id == alert_id)
        if since is not None:
            statement = statement.where(ViolationRecord.occurred_at >= since)
        if until is not None:
            statement = statement.where(ViolationRecord.occurred_at <= until)

        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                ViolationRecord.description.ilike(pattern)
                | ViolationRecord.rule_name.ilike(pattern)
            )

        return statement

    def search(
        self,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        descending: bool = True,
        **criteria: Any,
    ) -> Page[ViolationRecord]:
        """Return a filtered, paginated page of violations.

        Args:
            page: 1-based page number.
            page_size: Rows per page.
            sort_by: Sort key from :attr:`sortable_fields`. Defaults to
                the time the violation occurred.
            descending: Whether to sort descending.
            **criteria: Any argument accepted by :meth:`build_query`.

        Returns:
            The matching page.
        """
        return self.paginate(
            page=page,
            page_size=page_size,
            order_by=self.resolve_sort(sort_by) or ViolationRecord.occurred_at,
            descending=descending,
            statement=self.build_query(**criteria),
        )

    def for_alert(self, alert_id: str) -> List[ViolationRecord]:
        """Return every violation recorded against an alert.

        Args:
            alert_id: The owning alert's domain ID.

        Returns:
            The violations, oldest first.
        """
        return self.list(
            order_by=ViolationRecord.occurred_at, descending=False, alert_id=alert_id
        )

    def count_by_rule(self) -> Dict[str, int]:
        """Return the number of violations raised by each rule.

        Returns:
            A ``{rule_name: count}`` mapping.
        """
        rows = self.session.execute(
            select(ViolationRecord.rule_name, func.count()).group_by(
                ViolationRecord.rule_name
            )
        ).all()
        return {rule: int(count) for rule, count in rows}


class TrackRepository(BaseRepository[TrackRecord]):
    """Persistence for tracked-object lifetimes."""

    model = TrackRecord
    sortable_fields = {
        "first_seen": "first_seen",
        "last_seen": "last_seen",
        "track_id": "track_id",
        "class_name": "class_name",
        "confidence": "confidence",
        "observation_count": "observation_count",
        "created_at": "created_at",
    }

    @staticmethod
    def to_values(tracked_object: Any, run_id: str) -> Dict[str, Any]:
        """Map a domain tracked object onto column values.

        Args:
            tracked_object: An object shaped like
                :class:`app.tracking.tracked_object.TrackedObject`.
            run_id: Identity of the pipeline run this observation came
                from. See :class:`TrackRecord` for why this is required
                — ``track_id`` alone is not a stable identity across
                pipeline restarts.

        Returns:
            Column values for the new row.
        """
        box = getattr(tracked_object, "bounding_box", None)
        coordinates = (
            (box.x1, box.y1, box.x2, box.y2) if box is not None else None
        )

        return {
            "run_id": str(run_id),
            "track_id": int(tracked_object.track_id),
            "class_id": getattr(tracked_object, "class_id", None),
            "class_name": str(tracked_object.class_name),
            "confidence": float(getattr(tracked_object, "confidence", 0.0)),
            "first_seen": epoch_to_datetime(tracked_object.timestamp),
            "last_seen": epoch_to_datetime(tracked_object.timestamp),
            "first_frame": getattr(tracked_object, "frame_number", None),
            "last_frame": getattr(tracked_object, "frame_number", None),
            "observation_count": 1,
            "bounding_box": _box_to_json(coordinates),
        }

    def save_domain(self, tracked_object: Any, run_id: str) -> TrackRecord:
        """Insert or extend the record for a tracked object.

        A track observed across many frames should produce one row
        describing its whole appearance, not one row per frame — so an
        existing record for the same identity is extended.

        ``run_id`` is a required part of that identity, not an optional
        extra: ByteTrack restarts its ``track_id`` counter from 1 on
        every pipeline start, so looking up by ``track_id`` alone would
        match — and silently overwrite — an unrelated object's row from
        a previous run. The lookup below is always scoped to both
        columns together; there is deliberately no code path here that
        can match on ``track_id`` alone.

        Args:
            tracked_object: The tracked object to persist.
            run_id: Identity of the current pipeline run. Callers must
                mint one value per pipeline/tracker lifetime (see
                :class:`~app.streaming.persistence.LivePersistence`) and
                reuse it for every track observed during that run.

        Returns:
            The persisted record.
        """
        values = self.to_values(tracked_object, run_id)
        existing = self.first(track_id=values["track_id"], run_id=values["run_id"])

        if existing is None:
            return self.create(**values)

        return self.update_instance(
            existing,
            last_seen=values["last_seen"],
            last_frame=values["last_frame"],
            bounding_box=values["bounding_box"],
            confidence=values["confidence"],
            observation_count=(existing.observation_count or 0) + 1,
        )

    def build_query(
        self,
        track_id: Optional[int] = None,
        class_name: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        min_observations: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Select:
        """Build a filtered ``SELECT`` for track records.

        Args:
            track_id: Match this track identity.
            class_name: Match this object class.
            since: Only tracks first seen at or after this time.
            until: Only tracks first seen at or before this time.
            min_observations: Only tracks observed at least this often.
            search: Case-insensitive substring matched against the
                class name.

        Returns:
            The filtered statement.
        """
        statement = select(TrackRecord)

        if track_id is not None:
            statement = statement.where(TrackRecord.track_id == track_id)
        if class_name is not None:
            statement = statement.where(TrackRecord.class_name == class_name)
        if since is not None:
            statement = statement.where(TrackRecord.first_seen >= since)
        if until is not None:
            statement = statement.where(TrackRecord.first_seen <= until)
        if min_observations is not None:
            statement = statement.where(
                TrackRecord.observation_count >= min_observations
            )
        if search:
            statement = statement.where(
                TrackRecord.class_name.ilike(f"%{search.strip()}%")
            )

        return statement

    def search(
        self,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        descending: bool = True,
        **criteria: Any,
    ) -> Page[TrackRecord]:
        """Return a filtered, paginated page of tracks.

        Args:
            page: 1-based page number.
            page_size: Rows per page.
            sort_by: Sort key from :attr:`sortable_fields`. Defaults to
                when the track was first seen.
            descending: Whether to sort descending.
            **criteria: Any argument accepted by :meth:`build_query`.

        Returns:
            The matching page.
        """
        return self.paginate(
            page=page,
            page_size=page_size,
            order_by=self.resolve_sort(sort_by) or TrackRecord.first_seen,
            descending=descending,
            statement=self.build_query(**criteria),
        )

    def count_by_class(self) -> Dict[str, int]:
        """Return the number of tracks recorded per object class.

        Returns:
            A ``{class_name: count}`` mapping.
        """
        rows = self.session.execute(
            select(TrackRecord.class_name, func.count()).group_by(
                TrackRecord.class_name
            )
        ).all()
        return {name: int(count) for name, count in rows}


class SystemRepository(BaseRepository[SystemEvent]):
    """Persistence for system-level operational events."""

    model = SystemEvent
    sortable_fields = {
        "occurred_at": "occurred_at",
        "event_type": "event_type",
        "level": "level",
        "source": "source",
        "created_at": "created_at",
    }

    def log_event(
        self,
        event_type: str,
        message: str,
        level: str = "info",
        source: Optional[str] = None,
        occurred_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SystemEvent:
        """Record a system event.

        Args:
            event_type: Machine-readable event type, e.g.
                ``"pipeline_started"``.
            message: Human-readable description.
            level: Severity of the event.
            source: Component that emitted it.
            occurred_at: When it happened. Defaults to now.
            metadata: Free-form supporting detail.

        Returns:
            The persisted event.
        """
        return self.create(
            event_type=event_type,
            message=message,
            level=level,
            source=source,
            occurred_at=occurred_at or utcnow(),
            extra_metadata=metadata,
        )

    def build_query(
        self,
        event_type: Optional[str] = None,
        level: Optional[str] = None,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> Select:
        """Build a filtered ``SELECT`` for system events.

        Args:
            event_type: Match this event type.
            level: Match this severity.
            source: Match this emitting component.
            since: Only events at or after this time.
            until: Only events at or before this time.
            search: Case-insensitive substring matched against the
                message and event type.

        Returns:
            The filtered statement.
        """
        statement = select(SystemEvent)

        if event_type is not None:
            statement = statement.where(SystemEvent.event_type == event_type)
        if level is not None:
            statement = statement.where(SystemEvent.level == level)
        if source is not None:
            statement = statement.where(SystemEvent.source == source)
        if since is not None:
            statement = statement.where(SystemEvent.occurred_at >= since)
        if until is not None:
            statement = statement.where(SystemEvent.occurred_at <= until)

        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                SystemEvent.message.ilike(pattern)
                | SystemEvent.event_type.ilike(pattern)
            )

        return statement

    def search(
        self,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        descending: bool = True,
        **criteria: Any,
    ) -> Page[SystemEvent]:
        """Return a filtered, paginated page of events.

        Args:
            page: 1-based page number.
            page_size: Rows per page.
            sort_by: Sort key from :attr:`sortable_fields`. Defaults to
                the time the event occurred.
            descending: Whether to sort descending.
            **criteria: Any argument accepted by :meth:`build_query`.

        Returns:
            The matching page.
        """
        return self.paginate(
            page=page,
            page_size=page_size,
            order_by=self.resolve_sort(sort_by) or SystemEvent.occurred_at,
            descending=descending,
            statement=self.build_query(**criteria),
        )

    def recent(self, limit: int = 50) -> List[SystemEvent]:
        """Return the most recent system events.

        Args:
            limit: Maximum rows to return.

        Returns:
            The events, newest first.
        """
        return self.list(limit=limit, order_by=SystemEvent.occurred_at)

    def count_by_type(self) -> Dict[str, int]:
        """Return the number of events of each type.

        Returns:
            An ``{event_type: count}`` mapping.
        """
        rows = self.session.execute(
            select(SystemEvent.event_type, func.count()).group_by(
                SystemEvent.event_type
            )
        ).all()
        return {event_type: int(count) for event_type, count in rows}


@dataclass
class RepositoryBundle:
    """All repositories bound to a single session.

    Convenience for callers that need several repositories inside one
    transaction::

        with session_scope() as session:
            repos = RepositoryBundle.for_session(session)
            repos.alerts.save_domain(alert)
            repos.system.log_event("alert_persisted", "...")

    Attributes:
        alerts: Alert persistence.
        violations: Violation persistence.
        tracks: Track persistence.
        system: System-event persistence.
    """

    alerts: AlertRepository
    violations: ViolationRepository
    tracks: TrackRepository
    system: SystemRepository

    @classmethod
    def for_session(cls, session: Session) -> "RepositoryBundle":
        """Build every repository against one session.

        Args:
            session: The session providing the unit of work.

        Returns:
            The bundle of repositories.
        """
        return cls(
            alerts=AlertRepository(session),
            violations=ViolationRepository(session),
            tracks=TrackRepository(session),
            system=SystemRepository(session),
        )
