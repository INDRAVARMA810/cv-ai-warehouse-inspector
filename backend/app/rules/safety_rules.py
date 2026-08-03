"""Concrete warehouse safety rules.

Each rule here is pure business logic operating on tracked objects and
configured zones — no model inference, no I/O. Rules that depend on
capabilities the perception layer does not yet provide (notably PPE
classification) are present as explicit, disabled placeholders rather
than as silent gaps.
"""

from itertools import combinations
from typing import Any, List, Optional, Sequence, Tuple

from app.logger import logger
from app.rules.rule import BaseRule, RuleContext
from app.rules.rule_result import RuleViolation, Severity
from app.rules.zone import Zone, ZoneType


class RestrictedZoneRule(BaseRule):
    """Flags monitored objects that enter a restricted or danger zone."""

    default_severity: Severity = Severity.HIGH

    def __init__(
        self,
        monitored_classes: Optional[Sequence[str]] = None,
        zone_types: Optional[Sequence[ZoneType]] = None,
        use_box_overlap: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the rule.

        Args:
            monitored_classes: Class names this rule applies to.
                Defaults to ``("person",)``.
            zone_types: Zone types treated as off-limits. Defaults to
                danger and restricted zones.
            use_box_overlap: If ``True``, an object violates the rule
                when any part of its bounding box overlaps the zone. If
                ``False`` (default), only its center point is tested,
                which is less prone to false positives from loose boxes.
            **kwargs: Forwarded to :class:`BaseRule` (``name``,
                ``priority``, ``enabled``, ``severity``, ``description``).
        """
        kwargs.setdefault("priority", 10)
        kwargs.setdefault(
            "description", "Detects monitored objects inside restricted or danger zones."
        )
        super().__init__(**kwargs)

        self.monitored_classes = tuple(
            name.lower() for name in (monitored_classes or ("person",))
        )
        self.zone_types = tuple(zone_types or (ZoneType.DANGER, ZoneType.RESTRICTED))
        self.use_box_overlap = use_box_overlap

    def evaluate(self, context: RuleContext) -> List[RuleViolation]:
        """Check every monitored object against every off-limits zone.

        Args:
            context: The frame's evaluation context.

        Returns:
            One violation per object-zone intrusion.
        """
        violations: List[RuleViolation] = []

        target_zones = [
            zone for zone in context.zones.values() if zone.zone_type in self.zone_types
        ]
        if not target_zones:
            return violations

        for tracked_object in context.tracked_objects:
            class_name = str(getattr(tracked_object, "class_name", "")).lower()
            if class_name not in self.monitored_classes:
                continue

            box = self.box_of(tracked_object)
            center = self.center_of(tracked_object)

            for zone in target_zones:
                if not self._is_intruding(zone, box, center):
                    continue

                track_id = getattr(tracked_object, "track_id", None)
                violations.append(
                    self.build_violation(
                        description=(
                            f"{class_name} (track {track_id}) entered "
                            f"{zone.zone_type.value} zone '{zone.name}'"
                        ),
                        context=context,
                        track_id=track_id,
                        bounding_box=box,
                        severity=(
                            Severity.CRITICAL
                            if zone.zone_type == ZoneType.DANGER
                            else self.severity
                        ),
                        metadata={
                            "zone_name": zone.name,
                            "zone_type": zone.zone_type.value,
                            "class_name": class_name,
                            "detection_mode": (
                                "box_overlap" if self.use_box_overlap else "center_point"
                            ),
                        },
                    )
                )

        return violations

    def _is_intruding(
        self,
        zone: Zone,
        box: Optional[Tuple[float, float, float, float]],
        center: Optional[Tuple[float, float]],
    ) -> bool:
        """Return whether an object counts as inside the zone.

        Args:
            zone: The zone being tested.
            box: The object's bounding box, if available.
            center: The object's center point, if available.

        Returns:
            ``True`` if the object is intruding under the configured mode.
        """
        if self.use_box_overlap:
            return box is not None and zone.intersects_box(box)

        return center is not None and zone.contains_point(center)


class MinimumDistanceRule(BaseRule):
    """Flags pairs of objects that come closer than a safe separation.

    Distances are measured in **pixels** between bounding-box centers.
    Converting that to a real-world separation requires camera
    calibration (a homography onto the warehouse floor plane), which the
    perception layer does not yet provide — so ``min_distance`` is a
    pixel threshold that must be tuned per camera.
    """

    default_severity: Severity = Severity.HIGH

    def __init__(
        self,
        min_distance: float = 100.0,
        class_pairs: Optional[Sequence[Tuple[str, str]]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the rule.

        Args:
            min_distance: Minimum acceptable center-to-center distance,
                in pixels.
            class_pairs: Class-name pairs to check. Defaults to
                ``(("person", "forklift"),)``. Order within a pair does
                not matter.
            **kwargs: Forwarded to :class:`BaseRule`.

        Raises:
            ValueError: If ``min_distance`` is not positive.
        """
        kwargs.setdefault("priority", 20)
        kwargs.setdefault(
            "description", "Detects objects violating a minimum safe separation."
        )
        super().__init__(**kwargs)

        if min_distance <= 0:
            raise ValueError(f"min_distance must be positive, got {min_distance}")

        self.min_distance = float(min_distance)
        self.class_pairs = tuple(
            tuple(sorted((a.lower(), b.lower())))
            for a, b in (class_pairs or (("person", "forklift"),))
        )

    def evaluate(self, context: RuleContext) -> List[RuleViolation]:
        """Check every monitored object pair for unsafe proximity.

        Args:
            context: The frame's evaluation context.

        Returns:
            One violation per offending pair. Each pair is reported once,
            not once per participant.
        """
        violations: List[RuleViolation] = []

        for first, second in combinations(context.tracked_objects, 2):
            class_a = str(getattr(first, "class_name", "")).lower()
            class_b = str(getattr(second, "class_name", "")).lower()

            if tuple(sorted((class_a, class_b))) not in self.class_pairs:
                continue

            center_a = self.center_of(first)
            center_b = self.center_of(second)
            if center_a is None or center_b is None:
                continue

            distance = (
                (center_a[0] - center_b[0]) ** 2 + (center_a[1] - center_b[1]) ** 2
            ) ** 0.5

            if distance >= self.min_distance:
                continue

            track_a = getattr(first, "track_id", None)
            track_b = getattr(second, "track_id", None)

            violations.append(
                self.build_violation(
                    description=(
                        f"{class_a} (track {track_a}) and {class_b} (track {track_b}) "
                        f"are {distance:.1f}px apart, below the {self.min_distance:.1f}px minimum"
                    ),
                    context=context,
                    track_id=track_a,
                    bounding_box=self.box_of(first),
                    metadata={
                        "distance_px": round(distance, 2),
                        "min_distance_px": self.min_distance,
                        "track_ids": [track_a, track_b],
                        "class_names": [class_a, class_b],
                        "counterpart_bounding_box": self.box_of(second),
                    },
                )
            )

        return violations


class MaximumWorkersRule(BaseRule):
    """Flags frames where a class exceeds its permitted occupancy.

    Applies either to the whole frame or, when ``zone_name`` is set, to
    a single zone — useful for capacity limits on a loading bay or
    mezzanine.
    """

    default_severity: Severity = Severity.MEDIUM

    def __init__(
        self,
        max_count: int = 5,
        class_name: str = "person",
        zone_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the rule.

        Args:
            max_count: Maximum permitted simultaneous count.
            class_name: The class being limited.
            zone_name: Restrict counting to this zone. If ``None``, the
                whole frame is counted.
            **kwargs: Forwarded to :class:`BaseRule`.

        Raises:
            ValueError: If ``max_count`` is negative.
        """
        kwargs.setdefault("priority", 30)
        kwargs.setdefault(
            "description", "Detects when an occupancy limit is exceeded."
        )
        super().__init__(**kwargs)

        if max_count < 0:
            raise ValueError(f"max_count must be non-negative, got {max_count}")

        self.max_count = int(max_count)
        self.class_name = class_name.lower()
        self.zone_name = zone_name

    def evaluate(self, context: RuleContext) -> List[RuleViolation]:
        """Count monitored objects and compare against the limit.

        Args:
            context: The frame's evaluation context.

        Returns:
            A single violation if the limit is exceeded, otherwise empty.
            The violation carries no ``track_id``, since it concerns the
            scene rather than one object.
        """
        candidates = context.objects_of_class(self.class_name)
        zone: Optional[Zone] = None

        if self.zone_name is not None:
            zone = context.zones.get(self.zone_name)

            if zone is None:
                logger.warning(
                    f"Rule '{self.name}' references unknown zone "
                    f"'{self.zone_name}'; skipping evaluation."
                )
                return []

            candidates = [
                obj
                for obj in candidates
                if (center := self.center_of(obj)) is not None
                and zone.contains_point(center)
            ]

        count = len(candidates)
        if count <= self.max_count:
            return []

        location = f"zone '{self.zone_name}'" if self.zone_name else "frame"
        track_ids = [getattr(obj, "track_id", None) for obj in candidates]

        return [
            self.build_violation(
                description=(
                    f"{count} {self.class_name}(s) in {location}, "
                    f"exceeding the limit of {self.max_count}"
                ),
                context=context,
                metadata={
                    "count": count,
                    "max_count": self.max_count,
                    "class_name": self.class_name,
                    "zone_name": self.zone_name,
                    "track_ids": track_ids,
                },
            )
        ]


class PPEPlaceholderRule(BaseRule):
    """Placeholder for PPE compliance checking.

    PPE compliance (hard hats, hi-vis vests, safety boots) requires the
    perception layer to emit PPE-specific classes, which it does not yet
    do. This rule therefore ships **disabled by default** and always
    returns no violations.

    It exists so the wiring, configuration surface, and registration
    path for PPE checking are settled now, and so its absence is
    explicit rather than an unnoticed gap. Once PPE classes exist, the
    logic goes in :meth:`evaluate` and the default flips to enabled.
    """

    default_severity: Severity = Severity.HIGH

    def __init__(
        self,
        required_ppe: Optional[Sequence[str]] = None,
        monitored_classes: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the placeholder.

        Args:
            required_ppe: PPE class names that will be required once
                the perception layer can detect them. Defaults to
                ``("hard_hat", "safety_vest")``.
            monitored_classes: Classes the requirement will apply to.
                Defaults to ``("person",)``.
            **kwargs: Forwarded to :class:`BaseRule`. ``enabled``
                defaults to ``False``.
        """
        kwargs.setdefault("priority", 40)
        kwargs.setdefault("enabled", False)
        kwargs.setdefault(
            "description",
            "Placeholder for PPE compliance; inactive until PPE classes are available.",
        )
        super().__init__(**kwargs)

        self.required_ppe = tuple(required_ppe or ("hard_hat", "safety_vest"))
        self.monitored_classes = tuple(
            name.lower() for name in (monitored_classes or ("person",))
        )
        self._warned = False

    def evaluate(self, context: RuleContext) -> List[RuleViolation]:
        """Return no violations; PPE detection is not yet available.

        Args:
            context: The frame's evaluation context (unused).

        Returns:
            Always an empty list.
        """
        if not self._warned:
            logger.warning(
                f"Rule '{self.name}' is a placeholder and performs no PPE checking. "
                f"It will remain inert until the detection model emits PPE classes "
                f"({', '.join(self.required_ppe)})."
            )
            self._warned = True

        return []


#: The rules registered by default, in the order they are constructed.
#: :class:`~app.rules.rule_registry.RuleRegistry` uses this to build a
#: standard rule set; ``PPEPlaceholderRule`` is included but ships
#: disabled, so it is registered without being evaluated.
DEFAULT_RULES: Tuple[type, ...] = (
    RestrictedZoneRule,
    MinimumDistanceRule,
    MaximumWorkersRule,
    PPEPlaceholderRule,
)
