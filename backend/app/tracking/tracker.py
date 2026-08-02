"""High-level multi-object tracking orchestration.

Provides :class:`Tracker`, the single entry point the rest of the
application should use to turn per-frame detections into identity-stable
tracks. It owns no tracker-specific logic itself — that lives in
:mod:`app.tracking.bytetrack_engine` — so an appearance-based backend
(DeepSORT, StrongSORT) can be introduced later without changing this
interface.
"""

import time
from typing import Any, Dict, List, Optional

from app.logger import logger
from app.tracking.bytetrack_engine import (
    ByteTrackConfig,
    ByteTrackEngine,
    TrackingError,
)
from app.tracking.tracked_object import TrackedObject, TrackHistory


class Tracker:
    """Assigns and maintains stable identities across frames.

    Consumes the detection layer's ``DetectionResult`` objects and
    returns :class:`TrackedObject` instances, while retaining a rolling
    per-identity history for future motion analysis.

    Attributes:
        history_length: Observations retained per track identity.
    """

    def __init__(
        self,
        config: Optional[ByteTrackConfig] = None,
        frame_rate: int = 30,
        history_length: int = 60,
    ) -> None:
        """Configure the tracker and initialize its underlying engine.

        Args:
            config: ByteTrack tuning parameters. Defaults to
                :class:`ByteTrackConfig`.
            frame_rate: Frame rate of the source video, in frames per
                second.
            history_length: Number of observations retained per track.

        Raises:
            ValueError: If ``frame_rate`` or ``history_length`` is not
                positive.
            TrackerInitializationError: If the underlying engine cannot
                be constructed.
        """
        if history_length <= 0:
            raise ValueError(f"history_length must be positive, got {history_length}")

        self.history_length = history_length
        self._engine = ByteTrackEngine(config=config, frame_rate=frame_rate)
        self._histories: Dict[int, TrackHistory] = {}
        self._frame_number: int = 0

    @property
    def frame_number(self) -> int:
        """Number of frames processed since the last reset."""
        return self._frame_number

    @property
    def histories(self) -> Dict[int, TrackHistory]:
        """The rolling observation history, keyed by track ID."""
        return self._histories

    def update(self, detection_result: Any) -> List[TrackedObject]:
        """Advance tracking by one frame.

        Args:
            detection_result: The frame's
                :class:`app.detection.detection_result.DetectionResult`.

        Returns:
            The currently active tracked objects. Returns an empty list
            — rather than raising — if the input is unusable or the
            underlying tracker fails, so a single bad frame does not
            interrupt a running video pipeline.
        """
        self._frame_number += 1

        if detection_result is None:
            logger.warning(
                f"Tracker.update() received no detection result on frame "
                f"{self._frame_number}; skipping."
            )
            return []

        detections = getattr(detection_result, "detections", None)
        if detections is None:
            logger.warning(
                f"Tracker.update() received an object without a 'detections' "
                f"attribute on frame {self._frame_number}; skipping."
            )
            return []

        start_time = time.perf_counter()

        try:
            tracked_objects = self._engine.update(
                detections=detections,
                frame_number=self._frame_number,
                frame_shape=getattr(detection_result, "frame_shape", None),
            )
        except TrackingError as exc:
            logger.error(f"Tracking failed on frame {self._frame_number}: {exc}")
            return []

        self._record_histories(tracked_objects)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.debug(
            f"Tracked {len(tracked_objects)} object(s) from "
            f"{len(detections)} detection(s) in {elapsed_ms:.2f} ms "
            f"(frame {self._frame_number})."
        )

        return tracked_objects

    def _record_histories(self, tracked_objects: List[TrackedObject]) -> None:
        """Append this frame's observations to their per-identity histories.

        Args:
            tracked_objects: The frame's active tracked objects.
        """
        for tracked_object in tracked_objects:
            history = self._histories.get(tracked_object.track_id)

            if history is None:
                history = TrackHistory(
                    track_id=tracked_object.track_id,
                    max_length=self.history_length,
                )
                self._histories[tracked_object.track_id] = history

            history.add(tracked_object)

    def get_history(self, track_id: int) -> Optional[TrackHistory]:
        """Return the retained history for one track identity.

        Args:
            track_id: The identity to look up.

        Returns:
            The track's history, or ``None`` if the ID is unknown.
        """
        return self._histories.get(track_id)

    def reset(self) -> None:
        """Discard all tracking state, identities, and history.

        Call this when switching video sources so identities and history
        do not carry over between unrelated streams.
        """
        self._engine.reset()
        self._histories.clear()
        self._frame_number = 0
        logger.info("Tracker reset; all identities and history discarded.")
