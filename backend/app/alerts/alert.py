"""Core alert domain types.

An :class:`Alert` is the operational counterpart to a rule violation. A
violation is a momentary observation about one frame; an alert is a
durable, de-duplicated incident with a lifecycle — raised, escalated,
acknowledged by an operator, and finally resolved or expired.

These types are deliberately independent of the rule layer: severity
arrives as a plain integer level, so any violation-like source can feed
the alert system.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, Optional, Tuple


class AlertLevel(IntEnum):
    """Operational urgency of an alert, ordered least to most urgent.

    Numeric values intentionally mirror
    :class:`app.rules.rule_result.Severity`, so mapping between the two
    is lossless — but the enum is defined here so the alert layer does
    not depend on the rule layer.
    """

    INFO = 10
    LOW = 20
    MEDIUM = 30
    HIGH = 40
    CRITICAL = 50

    def __str__(self) -> str:
        """Return the lowercase level name, for logs and serialization."""
        return self.name.lower()

    @classmethod
    def from_severity(cls, severity: Any) -> "AlertLevel":
        """Map a rule-layer severity onto an alert level.

        Args:
            severity: A :class:`~app.rules.rule_result.Severity`, a bare
                integer of equivalent value, or a level name.

        Returns:
            The matching level. Unrecognized values fall back to the
            nearest defined level at or below the given value, and to
            :attr:`INFO` if there is none — an unknown severity should
            still surface, never vanish.
        """
        if isinstance(severity, cls):
            return severity

        if isinstance(severity, str):
            try:
                return cls[severity.strip().upper()]
            except KeyError:
                # A misspelled level name is a programmer error, not
                # runtime noise — fail loudly rather than downgrade it.
                raise ValueError(f"Unknown alert level name: {severity!r}") from None

        try:
            numeric = int(severity)
        except (TypeError, ValueError):
            return cls.INFO

        candidates = [level for level in cls if level.value <= numeric]
        return max(candidates) if candidates else cls.INFO


class AlertCategory(str, Enum):
    """What kind of hazard an alert concerns.

    Categories group alerts for routing and reporting independently of
    which specific rule fired, so notification policy and dashboards do
    not need updating every time a rule is added.
    """

    ZONE_INTRUSION = "zone_intrusion"
    PROXIMITY = "proximity"
    OCCUPANCY = "occupancy"
    PPE = "ppe"
    EQUIPMENT = "equipment"
    SYSTEM = "system"
    OTHER = "other"

    @classmethod
    def from_rule_name(cls, rule_name: str) -> "AlertCategory":
        """Infer a category from the name of the rule that fired.

        Args:
            rule_name: The originating rule's name.

        Returns:
            The inferred category, or :attr:`OTHER` when the rule name
            matches no known pattern.
        """
        name = (rule_name or "").lower()

        # Ordered longest-intent-first so, e.g., "zone" does not swallow
        # a rule whose name mentions both a zone and PPE.
        patterns = (
            (("ppe", "helmet", "hardhat", "hard_hat", "vest"), cls.PPE),
            (("distance", "proximity", "separation"), cls.PROXIMITY),
            (("worker", "occupancy", "capacity", "maximum"), cls.OCCUPANCY),
            (("zone", "restricted", "danger", "intrusion"), cls.ZONE_INTRUSION),
            (("equipment", "forklift", "machine", "vehicle"), cls.EQUIPMENT),
            (("system", "health", "camera", "model"), cls.SYSTEM),
        )

        for keywords, category in patterns:
            if any(keyword in name for keyword in keywords):
                return category

        return cls.OTHER


class AlertStatus(str, Enum):
    """Where an alert sits in its lifecycle.

    Transitions are one-way: ``ACTIVE`` may become ``ACKNOWLEDGED``,
    ``RESOLVED`` or ``EXPIRED``; ``ACKNOWLEDGED`` may become
    ``RESOLVED`` or ``EXPIRED``. ``RESOLVED`` and ``EXPIRED`` are
    terminal, so an incident's audit trail cannot be silently reopened.

    Attributes:
        ACTIVE: Raised and awaiting operator attention.
        ACKNOWLEDGED: Seen by an operator; the hazard may still persist.
        RESOLVED: The underlying hazard is no longer present.
        EXPIRED: Aged out without explicit resolution.
    """

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"

    @property
    def is_terminal(self) -> bool:
        """Whether no further transition is permitted from this status."""
        return self in (AlertStatus.RESOLVED, AlertStatus.EXPIRED)

    @property
    def is_open(self) -> bool:
        """Whether the alert still represents a live concern."""
        return self in (AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED)


@dataclass
class Alert:
    """A durable safety incident derived from one or more violations.

    An alert persists across frames: while the same hazard keeps being
    observed, the existing alert's :attr:`occurrence_count` and
    :attr:`last_seen` are updated rather than a new alert being raised.

    Attributes:
        rule_name: Name of the rule that raised the alert.
        level: Current urgency, which may exceed the original severity
            if the alert has escalated.
        category: The kind of hazard this alert concerns.
        message: Human-readable description of the hazard.
        alert_id: Unique identifier, generated on creation.
        timestamp: Unix timestamp (seconds) when the alert was raised.
        track_id: Identity of the object responsible, or ``None`` for
            scene-level alerts such as an occupancy limit.
        frame_number: Frame the alert was first raised from.
        bounding_box: Location of the offending object as
            ``(x1, y1, x2, y2)`` in pixels, if applicable.
        status: Current lifecycle status.
        metadata: Free-form supporting detail carried from the violation.
        initial_level: Urgency at creation, retained so escalation is
            visible after the fact.
        occurrence_count: How many times this hazard has been observed.
        first_seen: Timestamp of the first observation.
        last_seen: Timestamp of the most recent observation.
        acknowledged_at: When an operator acknowledged the alert.
        acknowledged_by: Who acknowledged it.
        resolved_at: When the alert was resolved or expired.
    """

    rule_name: str
    level: AlertLevel
    category: AlertCategory
    message: str

    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    track_id: Optional[int] = None
    frame_number: Optional[int] = None
    bounding_box: Optional[Tuple[float, float, float, float]] = None
    status: AlertStatus = AlertStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    initial_level: Optional[AlertLevel] = None
    occurrence_count: int = 1
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None

    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[float] = None

    def __post_init__(self) -> None:
        """Backfill derived timing and level fields."""
        if self.first_seen is None:
            self.first_seen = self.timestamp
        if self.last_seen is None:
            self.last_seen = self.timestamp
        if self.initial_level is None:
            self.initial_level = self.level

    @property
    def acknowledged(self) -> bool:
        """Whether an operator has acknowledged this alert."""
        return self.status == AlertStatus.ACKNOWLEDGED or self.acknowledged_at is not None

    @property
    def resolved(self) -> bool:
        """Whether this alert has been resolved."""
        return self.status == AlertStatus.RESOLVED

    @property
    def is_open(self) -> bool:
        """Whether this alert still represents a live concern."""
        return self.status.is_open

    @property
    def was_escalated(self) -> bool:
        """Whether the alert's urgency has risen since it was raised."""
        return self.initial_level is not None and self.level > self.initial_level

    @property
    def duration(self) -> float:
        """Seconds between the first and most recent observation."""
        if self.first_seen is None or self.last_seen is None:
            return 0.0
        return max(0.0, self.last_seen - self.first_seen)

    def age(self, now: Optional[float] = None) -> float:
        """Return how long ago the alert was last observed.

        Args:
            now: Timestamp to measure against. Defaults to the current
                time.

        Returns:
            Seconds since :attr:`last_seen`.
        """
        current = time.time() if now is None else now
        return max(0.0, current - (self.last_seen or self.timestamp))

    def register_occurrence(
        self,
        now: Optional[float] = None,
        frame_number: Optional[int] = None,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
    ) -> None:
        """Record that the same hazard was observed again.

        Args:
            now: Observation timestamp. Defaults to the current time.
            frame_number: Frame the observation came from, if known.
            bounding_box: Updated location of the offending object.
        """
        self.occurrence_count += 1
        self.last_seen = time.time() if now is None else now

        if frame_number is not None:
            self.metadata["last_frame_number"] = frame_number
        if bounding_box is not None:
            self.bounding_box = bounding_box

    def escalate(self, level: AlertLevel, reason: Optional[str] = None) -> bool:
        """Raise the alert's urgency.

        Escalation is one-way: a request to lower the level is ignored,
        so a hazard that briefly looks less serious cannot quietly
        downgrade an incident an operator is already reacting to.

        Args:
            level: The proposed new level.
            reason: Optional explanation, recorded in metadata.

        Returns:
            ``True`` if the level was raised, ``False`` otherwise.
        """
        if level <= self.level:
            return False

        previous = self.level
        self.level = level
        self.metadata.setdefault("escalations", []).append(
            {
                "from": str(previous),
                "to": str(level),
                "reason": reason or "severity increased",
            }
        )
        return True

    def acknowledge(
        self, by: Optional[str] = None, now: Optional[float] = None
    ) -> bool:
        """Mark the alert as seen by an operator.

        Args:
            by: Identifier of the acknowledging operator.
            now: Timestamp of the acknowledgement. Defaults to now.

        Returns:
            ``True`` if the alert transitioned, ``False`` if it was
            already acknowledged or in a terminal state.
        """
        if self.status != AlertStatus.ACTIVE:
            return False

        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = time.time() if now is None else now
        self.acknowledged_by = by
        return True

    def resolve(self, now: Optional[float] = None) -> bool:
        """Mark the underlying hazard as no longer present.

        Args:
            now: Timestamp of resolution. Defaults to the current time.

        Returns:
            ``True`` if the alert transitioned, ``False`` if it was
            already in a terminal state.
        """
        if self.status.is_terminal:
            return False

        self.status = AlertStatus.RESOLVED
        self.resolved_at = time.time() if now is None else now
        return True

    def expire(self, now: Optional[float] = None) -> bool:
        """Age the alert out without explicit resolution.

        Args:
            now: Timestamp of expiry. Defaults to the current time.

        Returns:
            ``True`` if the alert transitioned, ``False`` if it was
            already in a terminal state.
        """
        if self.status.is_terminal:
            return False

        self.status = AlertStatus.EXPIRED
        self.resolved_at = time.time() if now is None else now
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the alert.

        Returns:
            A plain dictionary with enums rendered as strings and the
            bounding box as a list.
        """
        return {
            "alert_id": self.alert_id,
            "timestamp": self.timestamp,
            "rule_name": self.rule_name,
            "level": str(self.level),
            "initial_level": str(self.initial_level) if self.initial_level else None,
            "category": self.category.value,
            "status": self.status.value,
            "message": self.message,
            "track_id": self.track_id,
            "frame_number": self.frame_number,
            "bounding_box": list(self.bounding_box) if self.bounding_box else None,
            "acknowledged": self.acknowledged,
            "acknowledged_at": self.acknowledged_at,
            "acknowledged_by": self.acknowledged_by,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
            "occurrence_count": self.occurrence_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "duration": self.duration,
            "was_escalated": self.was_escalated,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        """Return a concise developer-facing representation."""
        return (
            f"Alert(id={self.alert_id[:8]}, rule={self.rule_name!r}, "
            f"level={self.level!s}, status={self.status.value}, "
            f"track={self.track_id}, count={self.occurrence_count})"
        )
