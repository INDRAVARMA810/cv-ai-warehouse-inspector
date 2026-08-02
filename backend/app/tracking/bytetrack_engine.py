"""ByteTrack multi-object tracking engine.

Wraps Ultralytics' ``BYTETracker`` behind a narrow interface: given the
detections for one frame, return structured :class:`TrackedObject`
instances with stable identities. Contains no drawing, alerting, or
higher-level orchestration — see :mod:`app.tracking.tracker` for that.

ByteTrack is purely geometric (IoU + Kalman motion prediction) and runs
identically on CPU or GPU, so this engine has no device concept. A
future appearance-based engine (DeepSORT, StrongSORT) would add one.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.logger import logger
from app.tracking.tracked_object import BoundingBoxReference, TrackedObject, TrackState
from app.tracking.tracker_utils import detections_to_arrays, is_valid_track

try:
    from ultralytics.trackers.byte_tracker import BYTETracker
except ImportError as exc:  # ultralytics is optional until tracking is actually used
    BYTETracker = None  # type: ignore[assignment]
    _IMPORT_ERROR: Optional[ImportError] = exc
else:
    _IMPORT_ERROR = None


class TrackerInitializationError(Exception):
    """Raised when the underlying tracker cannot be constructed."""


class TrackingError(Exception):
    """Raised when a tracker update fails for a given frame."""


@dataclass
class ByteTrackConfig:
    """Tuning parameters for :class:`ByteTrackEngine`.

    Field names intentionally match those Ultralytics' ``BYTETracker``
    reads off its ``args`` object, so instances can be handed to it
    directly.

    Attributes:
        track_high_thresh: Confidence above which detections are used
            for the first association pass.
        track_low_thresh: Confidence below which detections are
            discarded entirely. Detections between the low and high
            thresholds feed ByteTrack's second association pass — the
            core idea that lets it recover occluded objects.
        new_track_thresh: Confidence required for an unmatched
            detection to start a brand-new track.
        track_buffer: Number of frames a lost track is retained before
            being removed, allowing re-identification after occlusion.
        match_thresh: IoU-distance threshold for accepting an
            association between a track and a detection.
        fuse_score: Whether to fuse confidence scores into the
            association cost. Read by newer Ultralytics versions.
    """

    track_high_thresh: float = 0.5
    track_low_thresh: float = 0.1
    new_track_thresh: float = 0.6
    track_buffer: int = 30
    match_thresh: float = 0.8
    fuse_score: bool = True


class _DetectionAdapter:
    """Adapts detection arrays to the interface ``BYTETracker`` expects.

    Ultralytics' tracker reads ``.conf``, ``.xywh``, and ``.cls`` off a
    ``Boxes``-like object. This exposes exactly those attributes over
    plain NumPy arrays, avoiding a dependency on Ultralytics' result
    types.
    """

    def __init__(self, boxes_cxcywh: np.ndarray, scores: np.ndarray, class_ids: np.ndarray) -> None:
        """Store the per-frame detection arrays.

        Args:
            boxes_cxcywh: Boxes of shape ``(N, 4)`` in center + size form.
            scores: Confidence scores of shape ``(N,)``.
            class_ids: Class indices of shape ``(N,)``.
        """
        self.xywh = boxes_cxcywh
        self.conf = scores
        self.cls = class_ids

    def __len__(self) -> int:
        """Return the number of detections held."""
        return len(self.conf)


class ByteTrackEngine:
    """Assigns stable identities to per-frame detections using ByteTrack.

    Attributes:
        config: The tuning parameters in effect.
        frame_rate: Source frame rate, used to size the lost-track buffer.
    """

    def __init__(
        self,
        config: Optional[ByteTrackConfig] = None,
        frame_rate: int = 30,
    ) -> None:
        """Construct and initialize the underlying ByteTrack tracker.

        Args:
            config: Tuning parameters. Defaults to :class:`ByteTrackConfig`.
            frame_rate: Frame rate of the source video, in frames per
                second. ByteTrack scales its lost-track buffer by this.

        Raises:
            ValueError: If ``frame_rate`` is not positive.
            TrackerInitializationError: If Ultralytics is not installed
                or the tracker cannot be constructed.
        """
        if frame_rate <= 0:
            raise ValueError(f"frame_rate must be positive, got {frame_rate}")

        self.config = config or ByteTrackConfig()
        self.frame_rate = frame_rate
        self._tracker: Any = None

        self._initialize_tracker()

    def _initialize_tracker(self) -> None:
        """Create a fresh ``BYTETracker``, discarding any existing state.

        Raises:
            TrackerInitializationError: If Ultralytics is not installed
                or construction fails.
        """
        if BYTETracker is None:
            raise TrackerInitializationError(
                "ultralytics is not installed. Install it with "
                "`pip install ultralytics` to enable ByteTrack tracking."
            ) from _IMPORT_ERROR

        try:
            self._tracker = BYTETracker(args=self.config, frame_rate=self.frame_rate)
        except Exception as exc:
            raise TrackerInitializationError(
                f"Failed to initialize ByteTrack: {exc}"
            ) from exc

        logger.info(
            f"ByteTrackEngine initialized: frame_rate={self.frame_rate}, "
            f"high_thresh={self.config.track_high_thresh}, "
            f"match_thresh={self.config.match_thresh}, "
            f"buffer={self.config.track_buffer}"
        )

    def reset(self) -> None:
        """Discard all track state and identities.

        Call this when switching to a different video source, so track
        IDs do not carry over between unrelated streams.
        """
        self._initialize_tracker()
        logger.info("ByteTrackEngine state reset; track IDs restart from 1.")

    def update(
        self,
        detections: Sequence[Any],
        frame_number: int,
        frame_shape: Optional[Tuple[int, int]] = None,
    ) -> List[TrackedObject]:
        """Advance the tracker by one frame.

        Args:
            detections: Detections for this frame — any objects exposing
                ``confidence``, ``class_id``, and a ``bounding_box``.
            frame_number: Index of the frame being processed.
            frame_shape: Optional ``(height, width)`` of the source
                frame, used to reject implausible extrapolated boxes.

        Returns:
            The currently active tracked objects. May be empty, and may
            omit detections the tracker has not yet confirmed.

        Raises:
            TrackingError: If the underlying tracker fails.
        """
        boxes, scores, class_ids = detections_to_arrays(detections)
        adapter = _DetectionAdapter(boxes, scores, class_ids)

        try:
            raw_tracks = self._tracker.update(adapter)
        except Exception as exc:
            raise TrackingError(
                f"ByteTrack update failed on frame {frame_number}: {exc}"
            ) from exc

        return self._parse_tracks(
            raw_tracks,
            detections=detections,
            frame_number=frame_number,
            frame_shape=frame_shape,
        )

    def _parse_tracks(
        self,
        raw_tracks: Any,
        detections: Sequence[Any],
        frame_number: int,
        frame_shape: Optional[Tuple[int, int]],
    ) -> List[TrackedObject]:
        """Convert ByteTrack's raw output rows into :class:`TrackedObject`.

        ByteTrack returns rows of ``[x1, y1, x2, y2, track_id, score,
        cls, detection_index]``; older releases omit the trailing
        detection index. Both layouts are handled.

        Args:
            raw_tracks: The array returned by ``BYTETracker.update``.
            detections: The detections passed in for this frame, used to
                recover human-readable class names.
            frame_number: Index of the frame being processed.
            frame_shape: Optional ``(height, width)`` of the source frame.

        Returns:
            The parsed tracked objects, with invalid boxes filtered out.
        """
        tracked_objects: List[TrackedObject] = []

        if raw_tracks is None or len(raw_tracks) == 0:
            return tracked_objects

        class_name_by_id = self._build_class_name_map(detections)
        timestamp = time.time()

        # Iterate rows directly rather than coercing the whole result with
        # np.asarray: a ragged result would raise there, before the
        # per-row length check below could reject the offending rows.
        for row in raw_tracks:
            if len(row) < 7:
                logger.warning(
                    f"Skipping malformed track row with {len(row)} values on "
                    f"frame {frame_number}; expected at least 7."
                )
                continue

            try:
                bbox = (float(row[0]), float(row[1]), float(row[2]), float(row[3]))
                track_id = int(row[4])
                confidence = float(row[5])
                class_id = int(row[6])
            except (TypeError, ValueError) as exc:
                logger.warning(
                    f"Skipping unparsable track row on frame {frame_number}: {exc}"
                )
                continue

            if not is_valid_track(bbox, frame_shape=frame_shape):
                logger.debug(
                    f"Rejected implausible track box {bbox} on frame {frame_number}."
                )
                continue

            tracked_objects.append(
                TrackedObject(
                    track_id=track_id,
                    class_id=class_id,
                    class_name=class_name_by_id.get(class_id, str(class_id)),
                    confidence=confidence,
                    bounding_box=BoundingBoxReference(*bbox),
                    frame_number=frame_number,
                    timestamp=timestamp,
                    state=TrackState.TRACKED,
                )
            )

        return tracked_objects

    @staticmethod
    def _build_class_name_map(detections: Sequence[Any]) -> Dict[int, str]:
        """Map class IDs to names using this frame's detections.

        ByteTrack propagates only numeric class IDs, so names are
        recovered from the detections that produced them.

        Args:
            detections: The detections passed in for this frame.

        Returns:
            A ``{class_id: class_name}`` lookup.
        """
        return {
            int(detection.class_id): str(detection.class_name)
            for detection in detections
        }
