"""Structured, tracker-agnostic data types produced by the tracking engine.

These dataclasses form the stable contract between the tracking layer
(:mod:`app.tracking`) and any downstream consumer (a future rule engine,
dashboard, or alerting system), independent of which underlying tracker
(ByteTrack, DeepSORT, StrongSORT, ...) produced them.

Several fields — velocity, direction, and tracker state — are declared
here as forward-looking placeholders. They are populated on a
best-effort basis today and exist so motion analysis can be layered on
later without breaking this contract.
"""

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, List, Optional, Tuple


class TrackState(str, Enum):
    """Lifecycle state of a track.

    Mirrors the states common to ByteTrack-style trackers so the value
    stays meaningful if the underlying engine is swapped out.
    """

    NEW = "new"
    TRACKED = "tracked"
    LOST = "lost"
    REMOVED = "removed"


@dataclass
class BoundingBoxReference:
    """An axis-aligned bounding box in absolute pixel coordinates.

    Deliberately mirrors :class:`app.detection.detection_result.BoundingBox`
    rather than importing it, so the tracking layer does not depend on
    the detection layer's concrete types. Use :meth:`from_detection_box`
    to convert at the boundary.

    ``(x1, y1)`` is the top-left corner and ``(x2, y2)`` is the
    bottom-right corner, both in pixel units within the source frame.
    """

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        """Width of the box, in pixels."""
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        """Height of the box, in pixels."""
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        """Area of the box, in square pixels."""
        return max(0.0, self.width) * max(0.0, self.height)

    @property
    def center(self) -> Tuple[float, float]:
        """The ``(x, y)`` center point of the box."""
        return (self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0

    def to_xyxy(self) -> Tuple[float, float, float, float]:
        """Return the box as an ``(x1, y1, x2, y2)`` tuple."""
        return self.x1, self.y1, self.x2, self.y2

    def to_xywh(self) -> Tuple[float, float, float, float]:
        """Return the box as an ``(x, y, width, height)`` tuple."""
        return self.x1, self.y1, self.width, self.height

    @classmethod
    def from_detection_box(cls, box: object) -> "BoundingBoxReference":
        """Build a reference box from any object exposing ``x1/y1/x2/y2``.

        Accepts :class:`app.detection.detection_result.BoundingBox`
        without importing it, keeping the two layers decoupled.

        Args:
            box: Any object with float ``x1``, ``y1``, ``x2``, ``y2``
                attributes.

        Returns:
            An equivalent :class:`BoundingBoxReference`.

        Raises:
            AttributeError: If ``box`` lacks the required attributes.
        """
        return cls(
            x1=float(getattr(box, "x1")),
            y1=float(getattr(box, "y1")),
            x2=float(getattr(box, "x2")),
            y2=float(getattr(box, "y2")),
        )


@dataclass
class TrackedObject:
    """A single object observed at one point in time, with a stable identity.

    Attributes:
        track_id: Identity assigned by the tracker, stable across frames.
        class_id: Integer class index as defined by the source model.
        class_name: Human-readable class label.
        confidence: Detection confidence score, in ``[0, 1]``.
        bounding_box: The object's location within the frame.
        frame_number: Index of the frame this observation came from.
        timestamp: Unix timestamp (seconds) when the observation was made.
        state: Lifecycle state of the track at this observation.
        velocity: Placeholder for ``(vx, vy)`` in pixels per second.
            ``None`` until motion analysis is implemented.
        direction: Placeholder for heading in degrees, measured
            counter-clockwise from the positive x-axis. ``None`` until
            motion analysis is implemented.
    """

    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bounding_box: BoundingBoxReference
    frame_number: int
    timestamp: float
    state: TrackState = TrackState.TRACKED
    velocity: Optional[Tuple[float, float]] = None
    direction: Optional[float] = None

    @property
    def center(self) -> Tuple[float, float]:
        """The ``(x, y)`` center point of this observation's box."""
        return self.bounding_box.center


@dataclass
class TrackHistory:
    """The rolling observation history for a single track identity.

    Retains the most recent observations of one ``track_id`` so motion
    analysis (velocity, direction, dwell time, zone transitions) can be
    computed later without re-deriving identity.

    Attributes:
        track_id: The identity this history belongs to.
        max_length: Maximum number of observations retained; older
            entries are discarded as new ones arrive.
        observations: The retained observations, oldest first.
    """

    track_id: int
    max_length: int = 60
    observations: Deque[TrackedObject] = field(default_factory=deque)

    def __post_init__(self) -> None:
        """Enforce ``max_length`` on the underlying deque."""
        if self.max_length <= 0:
            raise ValueError(f"max_length must be positive, got {self.max_length}")
        self.observations = deque(self.observations, maxlen=self.max_length)

    def __len__(self) -> int:
        """Return the number of retained observations."""
        return len(self.observations)

    @property
    def is_empty(self) -> bool:
        """Whether no observations have been recorded yet."""
        return len(self.observations) == 0

    @property
    def latest(self) -> Optional[TrackedObject]:
        """The most recent observation, or ``None`` if empty."""
        return self.observations[-1] if self.observations else None

    @property
    def first(self) -> Optional[TrackedObject]:
        """The oldest retained observation, or ``None`` if empty."""
        return self.observations[0] if self.observations else None

    def add(self, observation: TrackedObject) -> None:
        """Append an observation to the history.

        Args:
            observation: The observation to record.

        Raises:
            ValueError: If the observation's ``track_id`` does not match
                this history's ``track_id``.
        """
        if observation.track_id != self.track_id:
            raise ValueError(
                f"Observation track_id {observation.track_id} does not match "
                f"history track_id {self.track_id}"
            )
        self.observations.append(observation)

    def centers(self) -> List[Tuple[float, float]]:
        """Return the center point of every retained observation, oldest first."""
        return [observation.center for observation in self.observations]

    def duration(self) -> float:
        """Return the elapsed time spanned by the retained observations.

        Returns:
            Seconds between the oldest and newest retained observation;
            ``0.0`` if fewer than two observations exist.
        """
        if len(self.observations) < 2:
            return 0.0
        return self.observations[-1].timestamp - self.observations[0].timestamp
