"""Structured, model-agnostic data types returned by the detection engine.

These dataclasses form the stable contract between the detection layer
(:mod:`app.detection`) and any downstream consumer (a future rule
engine, dashboard, or alerting system), independent of which
underlying model produced them.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class BoundingBox:
    """An axis-aligned bounding box in absolute pixel coordinates.

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


@dataclass
class Detection:
    """A single detected object within a frame.

    Attributes:
        class_id: Integer class index as defined by the source model.
        class_name: Human-readable class label.
        confidence: Detection confidence score, in ``[0, 1]``.
        bounding_box: The object's location within the frame.
    """

    class_id: int
    class_name: str
    confidence: float
    bounding_box: BoundingBox


@dataclass
class DetectionResult:
    """The full set of detections produced for a single frame.

    Attributes:
        detections: All detections found in the frame.
        frame_shape: ``(height, width)`` of the source frame, in
            pixels, or ``None`` if unavailable.
        model_name: Identifier of the model that produced these results.
        inference_time_ms: Wall-clock inference time, in milliseconds.
    """

    detections: List[Detection] = field(default_factory=list)
    frame_shape: Optional[Tuple[int, int]] = None
    model_name: Optional[str] = None
    inference_time_ms: Optional[float] = None

    def __len__(self) -> int:
        """Return the number of detections in this result."""
        return len(self.detections)

    @property
    def is_empty(self) -> bool:
        """Whether no objects were detected."""
        return len(self.detections) == 0

    def filter_by_class(self, class_name: str) -> List[Detection]:
        """Return only detections matching the given class name.

        Args:
            class_name: The class name to filter by.

        Returns:
            The subset of detections whose ``class_name`` matches.
        """
        return [d for d in self.detections if d.class_name == class_name]

    def filter_by_confidence(self, min_confidence: float) -> List[Detection]:
        """Return only detections at or above a confidence threshold.

        Args:
            min_confidence: Minimum confidence score, in ``[0, 1]``.

        Returns:
            The subset of detections meeting the threshold.
        """
        return [d for d in self.detections if d.confidence >= min_confidence]
