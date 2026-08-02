"""Stateless helper functions shared across tracking engines.

These utilities handle the mechanical work of moving between the
detection layer's types, the numeric array formats trackers expect, and
the tracking layer's own types. Keeping them here means a future
DeepSORT or StrongSORT engine can reuse the same conversions rather
than reimplementing them.
"""

import math
from typing import Any, List, Optional, Sequence, Tuple

import numpy as np

from app.tracking.tracked_object import BoundingBoxReference


def compute_center(bbox: Sequence[float]) -> Tuple[float, float]:
    """Return the center point of an ``(x1, y1, x2, y2)`` box.

    Args:
        bbox: Box coordinates in ``xyxy`` order.

    Returns:
        The ``(x, y)`` center point, in pixels.

    Raises:
        ValueError: If ``bbox`` does not contain exactly four values.
    """
    if len(bbox) != 4:
        raise ValueError(f"bbox must contain 4 values in xyxy order, got {len(bbox)}")

    x1, y1, x2, y2 = (float(value) for value in bbox)
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def euclidean_distance(
    point_a: Tuple[float, float], point_b: Tuple[float, float]
) -> float:
    """Return the Euclidean distance between two 2-D points.

    Args:
        point_a: The first ``(x, y)`` point.
        point_b: The second ``(x, y)`` point.

    Returns:
        The straight-line distance between the points, in pixels.
    """
    return math.dist(point_a, point_b)


def xyxy_to_xywh(bbox: Sequence[float]) -> Tuple[float, float, float, float]:
    """Convert a box from corner form to top-left + size form.

    Args:
        bbox: Box coordinates as ``(x1, y1, x2, y2)``.

    Returns:
        The box as ``(x, y, width, height)``.

    Raises:
        ValueError: If ``bbox`` does not contain exactly four values.
    """
    if len(bbox) != 4:
        raise ValueError(f"bbox must contain 4 values in xyxy order, got {len(bbox)}")

    x1, y1, x2, y2 = (float(value) for value in bbox)
    return x1, y1, x2 - x1, y2 - y1


def xywh_to_xyxy(bbox: Sequence[float]) -> Tuple[float, float, float, float]:
    """Convert a box from top-left + size form to corner form.

    Args:
        bbox: Box coordinates as ``(x, y, width, height)``.

    Returns:
        The box as ``(x1, y1, x2, y2)``.

    Raises:
        ValueError: If ``bbox`` does not contain exactly four values.
    """
    if len(bbox) != 4:
        raise ValueError(f"bbox must contain 4 values in xywh order, got {len(bbox)}")

    x, y, width, height = (float(value) for value in bbox)
    return x, y, x + width, y + height


def xyxy_to_cxcywh(bbox: Sequence[float]) -> Tuple[float, float, float, float]:
    """Convert a box from corner form to center + size form.

    This is the layout ByteTrack expects for its input boxes.

    Args:
        bbox: Box coordinates as ``(x1, y1, x2, y2)``.

    Returns:
        The box as ``(center_x, center_y, width, height)``.

    Raises:
        ValueError: If ``bbox`` does not contain exactly four values.
    """
    if len(bbox) != 4:
        raise ValueError(f"bbox must contain 4 values in xyxy order, got {len(bbox)}")

    x1, y1, x2, y2 = (float(value) for value in bbox)
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0, x2 - x1, y2 - y1


def detections_to_arrays(
    detections: Sequence[Any],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert detection objects into the numeric arrays trackers consume.

    Accepts any sequence of objects exposing ``confidence``,
    ``class_id``, and a ``bounding_box`` with ``x1/y1/x2/y2`` — notably
    :class:`app.detection.detection_result.Detection` — without
    importing the detection layer.

    Args:
        detections: The detections to convert.

    Returns:
        A ``(boxes_cxcywh, scores, class_ids)`` tuple, where
        ``boxes_cxcywh`` has shape ``(N, 4)`` and ``scores`` and
        ``class_ids`` have shape ``(N,)``. All arrays are ``float32``
        and are empty (but correctly shaped) when ``detections`` is
        empty.
    """
    if not detections:
        return (
            np.zeros((0, 4), dtype=np.float32),
            np.zeros((0,), dtype=np.float32),
            np.zeros((0,), dtype=np.float32),
        )

    boxes: List[Tuple[float, float, float, float]] = []
    scores: List[float] = []
    class_ids: List[float] = []

    for detection in detections:
        box = detection.bounding_box
        boxes.append(
            xyxy_to_cxcywh((box.x1, box.y1, box.x2, box.y2))
        )
        scores.append(float(detection.confidence))
        class_ids.append(float(detection.class_id))

    return (
        np.asarray(boxes, dtype=np.float32),
        np.asarray(scores, dtype=np.float32),
        np.asarray(class_ids, dtype=np.float32),
    )


def to_bounding_box_reference(bbox: Sequence[float]) -> BoundingBoxReference:
    """Build a :class:`BoundingBoxReference` from ``(x1, y1, x2, y2)`` values.

    Args:
        bbox: Box coordinates in ``xyxy`` order.

    Returns:
        The equivalent :class:`BoundingBoxReference`.

    Raises:
        ValueError: If ``bbox`` does not contain exactly four values.
    """
    if len(bbox) != 4:
        raise ValueError(f"bbox must contain 4 values in xyxy order, got {len(bbox)}")

    x1, y1, x2, y2 = (float(value) for value in bbox)
    return BoundingBoxReference(x1=x1, y1=y1, x2=x2, y2=y2)


def is_valid_track(
    bbox: Sequence[float],
    frame_shape: Optional[Tuple[int, int]] = None,
    min_area: float = 1.0,
) -> bool:
    """Validate a tracker-emitted box before it becomes a tracked object.

    Trackers extrapolate positions for temporarily occluded objects,
    which can yield degenerate or off-frame boxes. This filters those
    out before they reach downstream consumers.

    Args:
        bbox: Box coordinates in ``xyxy`` order.
        frame_shape: Optional ``(height, width)`` of the source frame.
            When provided, boxes lying entirely outside the frame are
            rejected.
        min_area: Minimum acceptable box area, in square pixels.

    Returns:
        ``True`` if the box is well-formed and plausible.
    """
    if len(bbox) != 4:
        return False

    x1, y1, x2, y2 = (float(value) for value in bbox)

    if not all(math.isfinite(value) for value in (x1, y1, x2, y2)):
        return False

    if x2 <= x1 or y2 <= y1:
        return False

    if (x2 - x1) * (y2 - y1) < min_area:
        return False

    if frame_shape is not None:
        height, width = frame_shape
        # Reject boxes that fall entirely outside the frame; partially
        # visible objects at the frame edge remain valid.
        if x2 <= 0 or y2 <= 0 or x1 >= width or y1 >= height:
            return False

    return True
