"""Multi-object tracking.

Provides a modular tracking architecture: a tracker-specific engine
(:class:`ByteTrackEngine`), a high-level orchestration class
(:class:`Tracker`), and tracker-agnostic result dataclasses. The split
between engine and orchestrator exists so an appearance-based backend
(DeepSORT, StrongSORT) can be added later without changing the public
:class:`Tracker` interface.
"""

from app.tracking.bytetrack_engine import (
    ByteTrackConfig,
    ByteTrackEngine,
    TrackerInitializationError,
    TrackingError,
)
from app.tracking.tracked_object import (
    BoundingBoxReference,
    TrackedObject,
    TrackHistory,
    TrackState,
)
from app.tracking.tracker import Tracker

__all__ = [
    "Tracker",
    "ByteTrackEngine",
    "ByteTrackConfig",
    "BoundingBoxReference",
    "TrackedObject",
    "TrackHistory",
    "TrackState",
    "TrackerInitializationError",
    "TrackingError",
]
