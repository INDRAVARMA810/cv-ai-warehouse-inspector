"""SQLAlchemy ORM models for the persistence layer.

Defines the tables that record what the safety system observed:
alerts, the violations behind them, the objects that were tracked, and
system-level events.

Two portability decisions are worth knowing about:

* **JSON columns** use ``JSONB`` on PostgreSQL — which is indexable and
  stored efficiently — and fall back to generic ``JSON`` elsewhere, so
  the same models can run against SQLite in tests.
* **Enums are stored as strings** rather than native PostgreSQL ``ENUM``
  types. Native enums require a schema migration to add a value, which
  makes adding an alert category or category unnecessarily expensive.
  Validity is enforced in the domain layer, where the enums live.

Timestamps are stored as timezone-aware ``DateTime`` columns because
they index and report far better than raw epoch floats. The domain
layer works in epoch seconds, so the repositories convert at the
boundary.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

#: JSON column type: JSONB on PostgreSQL, generic JSON elsewhere.
JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime.

    Returns:
        The current UTC time.
    """
    return datetime.now(timezone.utc)


def epoch_to_datetime(value: Optional[float]) -> Optional[datetime]:
    """Convert epoch seconds to a timezone-aware UTC datetime.

    Args:
        value: Unix timestamp in seconds, or ``None``.

    Returns:
        The converted datetime, or ``None`` if ``value`` was ``None``.
    """
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def datetime_to_epoch(value: Optional[datetime]) -> Optional[float]:
    """Convert a datetime to epoch seconds.

    Naive datetimes are assumed to be UTC, which is what the database
    returns on backends without timezone support.

    Args:
        value: The datetime to convert, or ``None``.

    Returns:
        Unix timestamp in seconds, or ``None``.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


class Base(DeclarativeBase):
    """Declarative base for every model in the persistence layer."""


class TimestampMixin:
    """Adds row-level audit timestamps.

    These describe when the *row* was written, which is distinct from
    when the event it describes occurred.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )


class AlertRecord(Base, TimestampMixin):
    """A persisted safety alert.

    Mirrors :class:`app.alerts.alert.Alert`, including its
    deduplication counters, so a single row represents one incident
    rather than one frame.
    """

    __tablename__ = "alert_records"
    __table_args__ = (
        Index("ix_alert_records_level_status", "level", "status"),
        Index("ix_alert_records_occurred_status", "occurred_at", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    #: Domain-level identifier (UUID) carried over from the alert layer.
    alert_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    rule_name: Mapped[str] = mapped_column(String(128), index=True)
    level: Mapped[str] = mapped_column(String(16), index=True)
    initial_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True, default="active")
    message: Mapped[str] = mapped_column(Text)

    track_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    frame_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bounding_box: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True
    )

    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    was_escalated: Mapped[bool] = mapped_column(Boolean, default=False)

    # ``metadata`` is reserved by SQLAlchemy's declarative API, so the
    # attribute is named differently from its column.
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONType, nullable=True
    )

    violations: Mapped[list["ViolationRecord"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return a concise developer-facing representation."""
        return (
            f"AlertRecord(id={self.id}, alert_id={self.alert_id[:8]!r}, "
            f"rule={self.rule_name!r}, level={self.level!r}, "
            f"status={self.status!r})"
        )


class ViolationRecord(Base, TimestampMixin):
    """A single rule violation observed in one frame.

    Violations are the raw evidence behind an alert. They are optional
    to persist at full frame rate — doing so is expensive — but are
    valuable for incident review and for tuning rule thresholds.
    """

    __tablename__ = "violation_records"
    __table_args__ = (
        Index("ix_violation_records_rule_occurred", "rule_name", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    #: Owning alert, when the violation was folded into one. Null for
    #: violations recorded outside an alert's lifetime.
    alert_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("alert_records.alert_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    rule_name: Mapped[str] = mapped_column(String(128), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    description: Mapped[str] = mapped_column(Text)

    track_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    frame_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bounding_box: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True
    )
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONType, nullable=True
    )

    alert: Mapped[Optional["AlertRecord"]] = relationship(back_populates="violations")

    def __repr__(self) -> str:
        """Return a concise developer-facing representation."""
        return (
            f"ViolationRecord(id={self.id}, rule={self.rule_name!r}, "
            f"severity={self.severity!r}, track={self.track_id})"
        )


class TrackRecord(Base, TimestampMixin):
    """The lifetime of one tracked object.

    One row per identity per appearance, summarizing where and for how
    long an object was observed. This supports dwell-time analysis and
    incident reconstruction without storing every frame.

    ``track_id`` alone is **not** a stable identity: ByteTrack restarts
    its counter from 1 every time the tracker is (re)constructed, which
    happens on every pipeline start. ``run_id`` disambiguates which
    pipeline run a given ``track_id`` belongs to, so two unrelated
    objects that both happen to be "track #1" in different runs are
    never merged into the same row. The two together —
    ``UNIQUE(run_id, track_id)`` — are the row's real identity.
    """

    __tablename__ = "track_records"
    __table_args__ = (
        Index("ix_track_records_class_first_seen", "class_name", "first_seen"),
        UniqueConstraint(
            "run_id", "track_id", name="uq_track_records_run_id_track_id"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    #: Identifies the pipeline run (one per tracker instance) this
    #: track ID was assigned within. Minted once per
    #: :class:`~app.streaming.persistence.LivePersistence` instance —
    #: see that module for exactly when a new value is generated.
    run_id: Mapped[str] = mapped_column(String(36), index=True)

    track_id: Mapped[int] = mapped_column(Integer, index=True)
    class_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    class_name: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_frame: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_frame: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    observation_count: Mapped[int] = mapped_column(Integer, default=1)

    bounding_box: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONType, nullable=True
    )
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONType, nullable=True
    )

    def __repr__(self) -> str:
        """Return a concise developer-facing representation."""
        return (
            f"TrackRecord(id={self.id}, run_id={self.run_id[:8]!r}, "
            f"track_id={self.track_id}, class={self.class_name!r}, "
            f"observations={self.observation_count})"
        )


class SystemEvent(Base, TimestampMixin):
    """An operational event from the system itself.

    Records things like pipeline start/stop, camera loss, model load
    failures, and configuration changes — the context an operator needs
    when reviewing why the system did or did not see something.
    """

    __tablename__ = "system_events"
    __table_args__ = (Index("ix_system_events_type_occurred", "event_type", "occurred_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    level: Mapped[str] = mapped_column(String(16), index=True, default="info")
    source: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    message: Mapped[str] = mapped_column(Text)
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata", JSONType, nullable=True
    )

    def __repr__(self) -> str:
        """Return a concise developer-facing representation."""
        return (
            f"SystemEvent(id={self.id}, type={self.event_type!r}, "
            f"level={self.level!r}, source={self.source!r})"
        )


#: Every model the migration helpers operate on.
ALL_MODELS = (AlertRecord, ViolationRecord, TrackRecord, SystemEvent)
