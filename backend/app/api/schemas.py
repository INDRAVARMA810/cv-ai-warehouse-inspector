"""Pydantic V2 request and response models for the REST API.

These schemas are the API's public contract. They are deliberately
separate from the ORM models in :mod:`app.database.models`: the
database schema can change without breaking clients, and internal
columns are never exposed by accident.

Enumerations mirror the domain vocabulary so FastAPI validates query
parameters and renders the allowed values into the OpenAPI document.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

ItemT = TypeVar("ItemT")


class AlertLevelSchema(str, Enum):
    """Urgency of an alert."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatusSchema(str, Enum):
    """Lifecycle status of an alert."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class AlertCategorySchema(str, Enum):
    """Kind of hazard an alert concerns."""

    ZONE_INTRUSION = "zone_intrusion"
    PROXIMITY = "proximity"
    OCCUPANCY = "occupancy"
    PPE = "ppe"
    EQUIPMENT = "equipment"
    SYSTEM = "system"
    OTHER = "other"


class SortOrder(str, Enum):
    """Direction of a sort."""

    ASC = "asc"
    DESC = "desc"


class BoundingBoxSchema(BaseModel):
    """An axis-aligned bounding box in absolute pixel coordinates."""

    model_config = ConfigDict(from_attributes=True)

    x1: float = Field(description="Left edge, in pixels.")
    y1: float = Field(description="Top edge, in pixels.")
    x2: float = Field(description="Right edge, in pixels.")
    y2: float = Field(description="Bottom edge, in pixels.")


class ORMModel(BaseModel):
    """Base for schemas populated from ORM rows.

    ``populate_by_name`` allows construction either from the ORM
    attribute (``extra_metadata``) or from the public field name
    (``metadata``), which keeps the JSON contract clean while the column
    keeps the name SQLAlchemy requires.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AlertResponse(ORMModel):
    """A safety alert as returned by the API."""

    id: int = Field(description="Internal row identifier.")
    alert_id: str = Field(description="Stable public alert identifier (UUID).")
    occurred_at: datetime = Field(description="When the alert was raised.")
    rule_name: str = Field(description="Rule that raised the alert.")
    level: str = Field(description="Current urgency level.")
    initial_level: Optional[str] = Field(
        default=None, description="Urgency at the time the alert was raised."
    )
    category: str = Field(description="Kind of hazard.")
    status: str = Field(description="Lifecycle status.")
    message: str = Field(description="Human-readable description.")

    track_id: Optional[int] = Field(
        default=None,
        description="Responsible object's track identity, or null for scene-level alerts.",
    )
    frame_number: Optional[int] = Field(default=None, description="Originating frame.")
    bounding_box: Optional[BoundingBoxSchema] = Field(
        default=None, description="Location of the offending object."
    )

    occurrence_count: int = Field(description="Times the hazard was observed.")
    first_seen: Optional[datetime] = Field(default=None, description="First observation.")
    last_seen: Optional[datetime] = Field(default=None, description="Most recent observation.")

    acknowledged: bool = Field(description="Whether an operator acknowledged the alert.")
    acknowledged_at: Optional[datetime] = Field(default=None, description="Acknowledgement time.")
    acknowledged_by: Optional[str] = Field(default=None, description="Acknowledging operator.")
    resolved: bool = Field(description="Whether the hazard has cleared.")
    resolved_at: Optional[datetime] = Field(default=None, description="Resolution time.")
    was_escalated: bool = Field(description="Whether urgency rose after the alert was raised.")

    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias="extra_metadata",
        description="Rule-specific supporting detail.",
    )
    created_at: datetime = Field(description="When the row was written.")


class ViolationResponse(ORMModel):
    """A single rule violation as returned by the API."""

    id: int = Field(description="Internal row identifier.")
    alert_id: Optional[str] = Field(
        default=None, description="Owning alert, if the violation was folded into one."
    )
    occurred_at: datetime = Field(description="When the violation was observed.")
    rule_name: str = Field(description="Rule that produced the violation.")
    severity: str = Field(description="Severity of the violation.")
    description: str = Field(description="Human-readable description.")
    track_id: Optional[int] = Field(default=None, description="Responsible track identity.")
    frame_number: Optional[int] = Field(default=None, description="Originating frame.")
    bounding_box: Optional[BoundingBoxSchema] = Field(
        default=None, description="Location of the offending object."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias="extra_metadata",
        description="Rule-specific supporting detail.",
    )
    created_at: datetime = Field(description="When the row was written.")


class TrackResponse(ORMModel):
    """A tracked object's observed lifetime as returned by the API."""

    id: int = Field(description="Internal row identifier.")
    track_id: int = Field(description="Tracker-assigned identity.")
    class_id: Optional[int] = Field(default=None, description="Model class index.")
    class_name: str = Field(description="Detected object class.")
    confidence: Optional[float] = Field(default=None, description="Detection confidence.")
    first_seen: datetime = Field(description="First observation.")
    last_seen: Optional[datetime] = Field(default=None, description="Most recent observation.")
    first_frame: Optional[int] = Field(default=None, description="First frame observed.")
    last_frame: Optional[int] = Field(default=None, description="Last frame observed.")
    observation_count: int = Field(description="Frames the object was observed in.")
    bounding_box: Optional[BoundingBoxSchema] = Field(
        default=None, description="Most recent known location."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, validation_alias="extra_metadata", description="Supporting detail."
    )
    created_at: datetime = Field(description="When the row was written.")


class SystemEventResponse(ORMModel):
    """An operational system event as returned by the API."""

    id: int = Field(description="Internal row identifier.")
    occurred_at: datetime = Field(description="When the event happened.")
    event_type: str = Field(description="Machine-readable event type.")
    level: str = Field(description="Event severity.")
    source: Optional[str] = Field(default=None, description="Component that emitted it.")
    message: str = Field(description="Human-readable description.")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, validation_alias="extra_metadata", description="Supporting detail."
    )
    created_at: datetime = Field(description="When the row was written.")


class PageMeta(BaseModel):
    """Pagination metadata accompanying a page of results."""

    total: int = Field(description="Total rows matching the query.")
    page: int = Field(description="1-based page number.")
    page_size: int = Field(description="Rows requested per page.")
    pages: int = Field(description="Total pages available.")
    has_next: bool = Field(description="Whether a further page exists.")
    has_previous: bool = Field(description="Whether an earlier page exists.")


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """A page of results plus its pagination metadata."""

    items: List[ItemT] = Field(description="The rows on this page.")
    meta: PageMeta = Field(description="Pagination metadata.")


class AlertSearchRequest(BaseModel):
    """Request body for the alert search endpoint.

    Every field is optional; omitted fields impose no constraint. This
    exists alongside ``GET /alerts`` because search criteria grow past
    what is comfortable — or safely cacheable — in a query string.
    """

    model_config = ConfigDict(extra="forbid")

    status: Optional[AlertStatusSchema] = Field(default=None, description="Match this status.")
    level: Optional[AlertLevelSchema] = Field(default=None, description="Match this exact level.")
    levels: Optional[List[AlertLevelSchema]] = Field(
        default=None, description="Match any of these levels."
    )
    category: Optional[AlertCategorySchema] = Field(
        default=None, description="Match this category."
    )
    rule_name: Optional[str] = Field(
        default=None, max_length=128, description="Match this originating rule."
    )
    track_id: Optional[int] = Field(default=None, ge=0, description="Match this track identity.")
    acknowledged: Optional[bool] = Field(default=None, description="Match acknowledgement state.")
    resolved: Optional[bool] = Field(default=None, description="Match resolution state.")
    since: Optional[datetime] = Field(default=None, description="Only alerts at or after this time.")
    until: Optional[datetime] = Field(default=None, description="Only alerts at or before this time.")
    search: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Case-insensitive substring matched against message and rule name.",
    )

    page: int = Field(default=1, ge=1, description="1-based page number.")
    page_size: int = Field(default=50, ge=1, le=500, description="Rows per page.")
    sort_by: Optional[str] = Field(
        default=None,
        description="Sort key. Unsupported keys fall back to the default ordering.",
    )
    order: SortOrder = Field(default=SortOrder.DESC, description="Sort direction.")


class ComponentHealth(BaseModel):
    """Health of one dependency."""

    name: str = Field(description="Component name.")
    healthy: bool = Field(description="Whether the component is usable.")
    detail: Optional[str] = Field(default=None, description="Extra context.")


class HealthResponse(BaseModel):
    """Service health as returned by the health endpoint."""

    status: str = Field(description="'ok' when every component is healthy, else 'degraded'.")
    application: str = Field(description="Application name.")
    version: str = Field(description="Application version.")
    components: List[ComponentHealth] = Field(description="Per-dependency health.")


class ErrorResponse(BaseModel):
    """The body returned for every error.

    A single, predictable error envelope means clients need only one
    parsing path regardless of which failure occurred.
    """

    error: str = Field(description="Short machine-readable error code.")
    detail: str = Field(description="Human-readable explanation.")
    status_code: int = Field(description="HTTP status code.")
    path: Optional[str] = Field(default=None, description="Request path that failed.")
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Field-level validation failures, when applicable."
    )


class AlertAcknowledgeRequest(BaseModel):
    """Request body for acknowledging an alert."""

    model_config = ConfigDict(extra="forbid")

    acknowledged_by: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Identifier of the operator acknowledging the alert.",
    )
