"""Abstract base class and evaluation context for safety rules.

Every rule in the system subclasses :class:`BaseRule` and receives a
:class:`RuleContext` describing one frame. Rules are pure functions of
that context: they inspect it and return violations, without mutating
state, drawing, persisting, or notifying anyone. That keeps them
trivially testable and lets the engine run them in any order.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.rules.rule_result import RuleViolation, Severity
from app.rules.zone import Zone


@dataclass
class RuleContext:
    """Everything a rule needs to evaluate a single frame.

    Passing one context object — rather than a long argument list — means
    new information can be made available to rules later without changing
    every rule's signature.

    Attributes:
        tracked_objects: The frame's tracked objects. Duck-typed on the
            tracking layer's ``TrackedObject`` (``track_id``,
            ``class_name``, ``bounding_box``, ``center``) so this layer
            does not depend on that one.
        frame_number: Index of the frame being evaluated.
        timestamp: Unix timestamp (seconds) of the frame. Defaults to
            the current time.
        frame_shape: ``(height, width)`` of the source frame, in pixels.
        zones: The zones configured for this camera, keyed by name.
        metadata: Free-form extra context (camera ID, shift, ...).
    """

    tracked_objects: Sequence[Any] = field(default_factory=list)
    frame_number: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    frame_shape: Optional[Tuple[int, int]] = None
    zones: Dict[str, Zone] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def objects_of_class(self, class_name: str) -> List[Any]:
        """Return the tracked objects matching a class name.

        Args:
            class_name: The class name to filter by, compared
                case-insensitively.

        Returns:
            The matching tracked objects.
        """
        target = class_name.lower()
        return [
            obj
            for obj in self.tracked_objects
            if str(getattr(obj, "class_name", "")).lower() == target
        ]

    def zones_of_type(self, zone_type: Any) -> List[Zone]:
        """Return the configured zones of a given type.

        Args:
            zone_type: The :class:`~app.rules.zone.ZoneType` to filter by.

        Returns:
            The matching zones.
        """
        return [zone for zone in self.zones.values() if zone.zone_type == zone_type]


class BaseRule(ABC):
    """Abstract base class for a safety rule.

    Subclasses implement :meth:`evaluate`, which inspects a
    :class:`RuleContext` and returns any violations found. Rules must not
    raise for ordinary "nothing wrong" outcomes — they return an empty
    list instead.

    Attributes:
        name: Unique, human-readable identifier for the rule.
        priority: Evaluation order; **lower values run first**. Use this
            to run cheap or broadly-scoped rules before expensive ones.
        enabled: Whether the engine should evaluate this rule.
        severity: Default severity for violations this rule raises.
        description: Human-readable explanation of what the rule checks.
    """

    #: Default severity applied to violations when a subclass does not
    #: specify one per-violation.
    default_severity: Severity = Severity.MEDIUM

    def __init__(
        self,
        name: Optional[str] = None,
        priority: int = 100,
        enabled: bool = True,
        severity: Optional[Severity] = None,
        description: str = "",
    ) -> None:
        """Initialize the rule.

        Args:
            name: Unique identifier. Defaults to the subclass name.
            priority: Evaluation order; lower values run first.
            enabled: Whether the engine should evaluate this rule.
            severity: Severity for violations this rule raises. Defaults
                to the subclass's ``default_severity``.
            description: Human-readable explanation of the check.

        Raises:
            ValueError: If ``name`` is provided but empty.
        """
        if name is not None and not name.strip():
            raise ValueError("Rule name must be a non-empty string.")

        self.name = name or type(self).__name__
        self.priority = priority
        self.enabled = enabled
        self.severity = severity if severity is not None else self.default_severity
        self.description = description or (type(self).__doc__ or "").strip().split("\n")[0]

    @abstractmethod
    def evaluate(self, context: RuleContext) -> List[RuleViolation]:
        """Evaluate this rule against a single frame.

        Args:
            context: The frame's evaluation context.

        Returns:
            Any violations found. Empty when the frame is compliant.
        """

    def build_violation(
        self,
        description: str,
        context: RuleContext,
        track_id: Optional[int] = None,
        bounding_box: Optional[Tuple[float, float, float, float]] = None,
        severity: Optional[Severity] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RuleViolation:
        """Construct a :class:`RuleViolation` attributed to this rule.

        Centralizes the boilerplate of stamping each violation with the
        rule's name, severity, and the frame's timing information.

        Args:
            description: Human-readable explanation of the violation.
            context: The context being evaluated.
            track_id: Identity of the offending object, if applicable.
            bounding_box: Location of the offending object as
                ``(x1, y1, x2, y2)``, if applicable.
            severity: Overrides this rule's default severity.
            metadata: Rule-specific supporting detail.

        Returns:
            The populated violation.
        """
        return RuleViolation(
            rule_name=self.name,
            severity=severity if severity is not None else self.severity,
            description=description,
            timestamp=context.timestamp,
            frame_number=context.frame_number,
            track_id=track_id,
            bounding_box=bounding_box,
            metadata=metadata or {},
        )

    @staticmethod
    def box_of(tracked_object: Any) -> Optional[Tuple[float, float, float, float]]:
        """Extract an ``(x1, y1, x2, y2)`` tuple from a tracked object.

        Args:
            tracked_object: An object exposing a ``bounding_box`` with
                ``x1``/``y1``/``x2``/``y2`` attributes.

        Returns:
            The box coordinates, or ``None`` if unavailable.
        """
        box = getattr(tracked_object, "bounding_box", None)
        if box is None:
            return None

        try:
            return (float(box.x1), float(box.y1), float(box.x2), float(box.y2))
        except AttributeError:
            return None

    @staticmethod
    def center_of(tracked_object: Any) -> Optional[Tuple[float, float]]:
        """Extract an object's ``(x, y)`` center point.

        Prefers the object's own ``center``, falling back to deriving it
        from the bounding box.

        Args:
            tracked_object: The object to inspect.

        Returns:
            The center point, or ``None`` if it cannot be determined.
        """
        center = getattr(tracked_object, "center", None)
        if center is not None:
            return (float(center[0]), float(center[1]))

        box = BaseRule.box_of(tracked_object)
        if box is None:
            return None

        x1, y1, x2, y2 = box
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def __repr__(self) -> str:
        """Return a concise developer-facing representation."""
        state = "enabled" if self.enabled else "disabled"
        return (
            f"{type(self).__name__}(name={self.name!r}, priority={self.priority}, "
            f"severity={self.severity!s}, {state})"
        )
