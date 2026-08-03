"""Spatial zone definitions used by the safety rule engine.

Zones describe regions of interest within a camera's field of view — a
restricted aisle, the swing radius around a machine, a designated safe
walkway — and answer the geometric questions rules need to ask: is this
object inside the zone, does it overlap the zone, how far away is it?

Coordinates are absolute pixels within the source frame, matching the
convention used by the detection and tracking layers.
"""

import math
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Sequence, Tuple

Point = Tuple[float, float]
Box = Tuple[float, float, float, float]


class ZoneType(str, Enum):
    """The safety meaning of a zone.

    Attributes:
        DANGER: An area hazardous by nature (machinery, loading bay).
            Presence is a violation for unauthorized classes.
        RESTRICTED: An area only specific roles or vehicles may enter.
        SAFE: A designated safe area, e.g. a marked pedestrian walkway.
            Used as a negative condition — being *outside* it may matter.
    """

    DANGER = "danger"
    RESTRICTED = "restricted"
    SAFE = "safe"


def _point_to_segment_distance(point: Point, start: Point, end: Point) -> float:
    """Return the shortest distance from a point to a line segment.

    Args:
        point: The ``(x, y)`` point to measure from.
        start: The segment's first endpoint.
        end: The segment's second endpoint.

    Returns:
        The perpendicular distance where it falls within the segment,
        otherwise the distance to the nearer endpoint.
    """
    px, py = point
    x1, y1 = start
    x2, y2 = end

    dx, dy = x2 - x1, y2 - y1
    segment_length_squared = dx * dx + dy * dy

    if segment_length_squared == 0.0:
        # Degenerate segment: both endpoints coincide.
        return math.dist(point, start)

    # Projection of the point onto the segment, clamped to its extent.
    t = ((px - x1) * dx + (py - y1) * dy) / segment_length_squared
    t = max(0.0, min(1.0, t))

    return math.dist(point, (x1 + t * dx, y1 + t * dy))


def _segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point) -> bool:
    """Return whether two line segments intersect.

    Uses the orientation (counter-clockwise) test, including the
    collinear-overlap case.

    Args:
        a1: First endpoint of segment A.
        a2: Second endpoint of segment A.
        b1: First endpoint of segment B.
        b2: Second endpoint of segment B.

    Returns:
        ``True`` if the segments touch or cross.
    """

    def orientation(p: Point, q: Point, r: Point) -> float:
        return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    def on_segment(p: Point, q: Point, r: Point) -> bool:
        return (
            min(p[0], r[0]) <= q[0] <= max(p[0], r[0])
            and min(p[1], r[1]) <= q[1] <= max(p[1], r[1])
        )

    o1 = orientation(a1, a2, b1)
    o2 = orientation(a1, a2, b2)
    o3 = orientation(b1, b2, a1)
    o4 = orientation(b1, b2, a2)

    if (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0):
        return True

    # Collinear cases.
    if o1 == 0 and on_segment(a1, b1, a2):
        return True
    if o2 == 0 and on_segment(a1, b2, a2):
        return True
    if o3 == 0 and on_segment(b1, a1, b2):
        return True
    if o4 == 0 and on_segment(b1, a2, b2):
        return True

    return False


class Zone(ABC):
    """Abstract base class for a named spatial region.

    Attributes:
        name: Human-readable identifier, unique within a deployment.
        zone_type: The safety meaning of this zone.
    """

    def __init__(self, name: str, zone_type: ZoneType = ZoneType.RESTRICTED) -> None:
        """Initialize the zone.

        Args:
            name: Human-readable identifier for the zone.
            zone_type: The safety meaning of this zone.

        Raises:
            ValueError: If ``name`` is empty.
        """
        if not name or not name.strip():
            raise ValueError("Zone name must be a non-empty string.")

        self.name = name
        self.zone_type = ZoneType(zone_type)

    @abstractmethod
    def contains_point(self, point: Point) -> bool:
        """Return whether a point lies inside the zone.

        Args:
            point: The ``(x, y)`` point to test, in pixels.

        Returns:
            ``True`` if the point is inside or on the zone boundary.
        """

    @abstractmethod
    def intersects_box(self, box: Box) -> bool:
        """Return whether an axis-aligned box overlaps the zone.

        Args:
            box: The box as ``(x1, y1, x2, y2)``, in pixels.

        Returns:
            ``True`` if any part of the box overlaps the zone.
        """

    @abstractmethod
    def distance_to(self, point: Point) -> float:
        """Return the shortest distance from a point to the zone.

        Args:
            point: The ``(x, y)`` point to measure from, in pixels.

        Returns:
            The distance in pixels, or ``0.0`` if the point is inside
            the zone.
        """

    @staticmethod
    def _box_corners(box: Box) -> List[Point]:
        """Return a box's four corners, clockwise from the top-left.

        Args:
            box: The box as ``(x1, y1, x2, y2)``.

        Returns:
            The corner points.
        """
        x1, y1, x2, y2 = box
        return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    def __repr__(self) -> str:
        """Return a concise developer-facing representation."""
        return f"{type(self).__name__}(name={self.name!r}, zone_type={self.zone_type.value!r})"


class RectangleZone(Zone):
    """An axis-aligned rectangular zone.

    Attributes:
        x1: Left edge, in pixels.
        y1: Top edge, in pixels.
        x2: Right edge, in pixels.
        y2: Bottom edge, in pixels.
    """

    def __init__(
        self,
        name: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        zone_type: ZoneType = ZoneType.RESTRICTED,
    ) -> None:
        """Initialize the rectangle, normalizing its corner order.

        Args:
            name: Human-readable identifier for the zone.
            x1: One horizontal edge, in pixels.
            y1: One vertical edge, in pixels.
            x2: The opposite horizontal edge, in pixels.
            y2: The opposite vertical edge, in pixels.
            zone_type: The safety meaning of this zone.

        Raises:
            ValueError: If the rectangle has zero width or height.
        """
        super().__init__(name=name, zone_type=zone_type)

        # Accept corners in any order.
        self.x1, self.x2 = float(min(x1, x2)), float(max(x1, x2))
        self.y1, self.y2 = float(min(y1, y2)), float(max(y1, y2))

        if self.x1 == self.x2 or self.y1 == self.y2:
            raise ValueError(
                f"Zone '{name}' is degenerate: width={self.x2 - self.x1}, "
                f"height={self.y2 - self.y1}"
            )

    @property
    def area(self) -> float:
        """Area of the zone, in square pixels."""
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    def contains_point(self, point: Point) -> bool:
        """Return whether a point lies inside the rectangle (boundary included).

        Args:
            point: The ``(x, y)`` point to test.

        Returns:
            ``True`` if the point is inside or on the boundary.
        """
        x, y = point
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def intersects_box(self, box: Box) -> bool:
        """Return whether an axis-aligned box overlaps the rectangle.

        Args:
            box: The box as ``(x1, y1, x2, y2)``.

        Returns:
            ``True`` if the two rectangles overlap or touch.
        """
        bx1, by1, bx2, by2 = box
        bx1, bx2 = min(bx1, bx2), max(bx1, bx2)
        by1, by2 = min(by1, by2), max(by1, by2)

        return not (
            bx2 < self.x1 or bx1 > self.x2 or by2 < self.y1 or by1 > self.y2
        )

    def distance_to(self, point: Point) -> float:
        """Return the shortest distance from a point to the rectangle.

        Args:
            point: The ``(x, y)`` point to measure from.

        Returns:
            The distance in pixels, or ``0.0`` if the point is inside.
        """
        x, y = point
        dx = max(self.x1 - x, 0.0, x - self.x2)
        dy = max(self.y1 - y, 0.0, y - self.y2)
        return math.hypot(dx, dy)


class PolygonZone(Zone):
    """An arbitrary simple polygon, for zones a rectangle cannot express.

    Attributes:
        points: The polygon's vertices, in order. The final vertex is
            implicitly connected back to the first.
    """

    def __init__(
        self,
        name: str,
        points: Sequence[Point],
        zone_type: ZoneType = ZoneType.RESTRICTED,
    ) -> None:
        """Initialize the polygon.

        Args:
            name: Human-readable identifier for the zone.
            points: At least three ``(x, y)`` vertices, in order.
            zone_type: The safety meaning of this zone.

        Raises:
            ValueError: If fewer than three vertices are supplied, or any
                vertex is not a 2-value coordinate pair.
        """
        super().__init__(name=name, zone_type=zone_type)

        if len(points) < 3:
            raise ValueError(
                f"Zone '{name}' needs at least 3 points to form a polygon, got {len(points)}"
            )

        for point in points:
            if len(point) != 2:
                raise ValueError(
                    f"Zone '{name}' has an invalid vertex {point!r}; expected (x, y)."
                )

        self.points: List[Point] = [(float(x), float(y)) for x, y in points]

    def edges(self) -> List[Tuple[Point, Point]]:
        """Return the polygon's edges as ``(start, end)`` point pairs."""
        return [
            (self.points[i], self.points[(i + 1) % len(self.points)])
            for i in range(len(self.points))
        ]

    def contains_point(self, point: Point) -> bool:
        """Return whether a point lies inside the polygon.

        Uses the ray-casting (even-odd) algorithm. Points lying exactly
        on an edge are treated as inside, so an object touching a zone
        boundary is not silently excluded.

        Args:
            point: The ``(x, y)`` point to test.

        Returns:
            ``True`` if the point is inside or on the boundary.
        """
        x, y = point

        # Treat boundary contact as inside.
        for start, end in self.edges():
            if _point_to_segment_distance(point, start, end) == 0.0:
                return True

        inside = False
        for (x1, y1), (x2, y2) in self.edges():
            # Does a horizontal ray from the point cross this edge?
            if (y1 > y) != (y2 > y):
                x_intersection = (x2 - x1) * (y - y1) / (y2 - y1) + x1
                if x < x_intersection:
                    inside = not inside

        return inside

    def intersects_box(self, box: Box) -> bool:
        """Return whether an axis-aligned box overlaps the polygon.

        Covers all three overlap cases: the box lying (partly) inside
        the polygon, the polygon lying inside the box, and their
        boundaries crossing.

        Args:
            box: The box as ``(x1, y1, x2, y2)``.

        Returns:
            ``True`` if any part of the box overlaps the polygon.
        """
        x1, y1, x2, y2 = box
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        corners = self._box_corners((x1, y1, x2, y2))

        # Case 1: a box corner sits inside the polygon.
        if any(self.contains_point(corner) for corner in corners):
            return True

        # Case 2: the polygon sits entirely inside the box.
        if any(x1 <= px <= x2 and y1 <= py <= y2 for px, py in self.points):
            return True

        # Case 3: an edge of each shape crosses the other.
        box_edges = [
            (corners[i], corners[(i + 1) % len(corners)]) for i in range(len(corners))
        ]
        return any(
            _segments_intersect(bs, be, ps, pe)
            for bs, be in box_edges
            for ps, pe in self.edges()
        )

    def distance_to(self, point: Point) -> float:
        """Return the shortest distance from a point to the polygon.

        Args:
            point: The ``(x, y)`` point to measure from.

        Returns:
            The distance in pixels to the nearest edge, or ``0.0`` if
            the point is inside.
        """
        if self.contains_point(point):
            return 0.0

        return min(
            _point_to_segment_distance(point, start, end) for start, end in self.edges()
        )
