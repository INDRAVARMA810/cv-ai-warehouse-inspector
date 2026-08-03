"""End-to-end AI warehouse safety inspection pipeline.

Wires the completed modules together into a single live pipeline::

    Camera -> ImagePreprocessor -> Detector -> Tracker -> RuleEngine -> Visualization

Every stage delegates to its existing module; this script contributes
only orchestration and rendering, which deliberately live outside the
library modules (they intentionally contain no drawing code).

Run from the ``backend/`` directory::

    python run_detection.py                      # default webcam, auto device
    python run_detection.py --source video.mp4   # a video file instead
    python run_detection.py --device cpu         # force CPU
    python run_detection.py --weights custom.pt  # custom-trained weights

Press ``Q`` to quit.
"""

import argparse
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union

import cv2
import numpy as np

from app.config import settings
from app.detection import Detector
from app.detection.detection_result import DetectionResult
from app.detection.model_loader import ModelLoadError, get_best_device
from app.image_processing import ImagePreprocessor
from app.logger import logger
from app.rules import (
    RectangleZone,
    RuleEngine,
    RuleResult,
    Severity,
    Zone,
    ZoneType,
)
from app.tracking import Tracker, TrackedObject, TrackerInitializationError
from app.video import Camera, CameraError, FPSCounter

WINDOW_NAME = "AI Warehouse Safety Inspector"
QUIT_KEY = "q"

#: Consecutive failed frame reads tolerated before the pipeline stops.
#: Webcams drop the occasional frame; a single miss should not end a session.
MAX_CONSECUTIVE_READ_FAILURES = 30

# BGR colors used by the overlay.
COLOR_OK = (0, 200, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_PANEL = (25, 25, 25)
COLOR_ZONE: Dict[ZoneType, Tuple[int, int, int]] = {
    ZoneType.DANGER: (0, 0, 220),
    ZoneType.RESTRICTED: (0, 140, 235),
    ZoneType.SAFE: (0, 180, 0),
}
COLOR_SEVERITY: Dict[Severity, Tuple[int, int, int]] = {
    Severity.INFO: (200, 200, 200),
    Severity.LOW: (0, 220, 220),
    Severity.MEDIUM: (0, 165, 255),
    Severity.HIGH: (0, 90, 255),
    Severity.CRITICAL: (0, 0, 255),
}

FONT = cv2.FONT_HERSHEY_SIMPLEX


@dataclass
class PipelineConfig:
    """Runtime configuration for :class:`SafetyPipeline`.

    Attributes:
        source: Webcam index or path to a video file.
        weights: YOLO weights path, or a built-in Ultralytics model name.
        device: Compute device (``"cuda"``/``"cpu"``), or ``None`` to
            select the best available automatically.
        confidence_threshold: Minimum detection confidence, in ``[0, 1]``.
        iou_threshold: NMS IoU threshold, in ``[0, 1]``.
        resize_to: ``(width, height)`` to resize frames to before
            inference, or ``None`` to keep the camera's native size.
        apply_clahe: Whether to apply CLAHE, which lifts contrast in the
            uneven lighting typical of warehouse interiors.
        frame_rate: Expected source frame rate, used to size ByteTrack's
            lost-track buffer.
        enable_zones: Whether to install the demonstration safety zones.
        max_violation_lines: Maximum violations listed in the overlay.
    """

    source: Union[int, str] = 0
    weights: str = "yolov8n.pt"
    device: Optional[str] = None
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    resize_to: Optional[Tuple[int, int]] = None
    apply_clahe: bool = True
    frame_rate: int = 30
    enable_zones: bool = True
    max_violation_lines: int = 5


@dataclass
class FrameOutcome:
    """Everything one frame produced, passed to the renderer.

    Attributes:
        frame: The preprocessed frame the rest of the stages saw.
        detection_result: Raw detections for the frame.
        tracked_objects: Identity-stable objects for the frame.
        rule_result: Safety evaluation for the frame.
    """

    frame: np.ndarray
    detection_result: DetectionResult
    tracked_objects: List[TrackedObject] = field(default_factory=list)
    rule_result: Optional[RuleResult] = None


class SafetyPipeline:
    """Runs the full detect-track-evaluate loop over a video source.

    Holds the per-stage components and the state that must persist
    across frames (tracker identities, FPS window, zone definitions).

    Attributes:
        config: The runtime configuration in effect.
        device: The compute device actually in use.
    """

    def __init__(self, config: PipelineConfig) -> None:
        """Build the pipeline's stages.

        Args:
            config: Runtime configuration.

        Raises:
            ModelLoadError: If the detection weights cannot be loaded.
            TrackerInitializationError: If ByteTrack cannot be created.
        """
        self.config = config

        # Resolve the device up front so it can be both handed to the
        # detector and reported on the overlay, without reaching into
        # the detector's internals.
        self.device: str = config.device or get_best_device()
        if config.device is None:
            logger.info(f"No device specified; selected '{self.device}' automatically.")

        self.detector = Detector(
            weights_path=config.weights,
            device=self.device,
            confidence_threshold=config.confidence_threshold,
            iou_threshold=config.iou_threshold,
        )
        self.tracker = Tracker(frame_rate=config.frame_rate)
        self.rule_engine = RuleEngine()
        self.fps_counter = FPSCounter()

        self._zones_installed = False

    def _install_zones(self, width: int, height: int) -> None:
        """Install demonstration safety zones sized to the frame.

        Zones are defined as fractions of the frame so they remain
        sensible whatever resolution the camera delivers. **These are
        demonstration zones**: a real deployment should load surveyed,
        per-camera zone geometry from configuration instead.

        Args:
            width: Frame width, in pixels.
            height: Frame height, in pixels.
        """
        if self._zones_installed or not self.config.enable_zones:
            return

        zones: Sequence[Zone] = (
            RectangleZone(
                name="machinery-bay",
                x1=0.02 * width,
                y1=0.45 * height,
                x2=0.38 * width,
                y2=0.98 * height,
                zone_type=ZoneType.DANGER,
            ),
            RectangleZone(
                name="loading-dock",
                x1=0.62 * width,
                y1=0.45 * height,
                x2=0.98 * width,
                y2=0.98 * height,
                zone_type=ZoneType.RESTRICTED,
            ),
        )

        self.rule_engine.add_zones(zones)
        self._zones_installed = True
        logger.info(
            f"Installed {len(zones)} demonstration zone(s) for a {width}x{height} frame: "
            f"{', '.join(zone.name for zone in zones)}"
        )

    def preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Apply the image processing stage to a raw camera frame.

        Only transformations that preserve the 8-bit BGR layout YOLO
        expects are applied. Normalization and RGB conversion are
        available on :class:`ImagePreprocessor` but are deliberately
        **not** used here: they would produce a float or channel-swapped
        image that Ultralytics would misinterpret.

        Args:
            frame: The raw BGR frame from the camera.

        Returns:
            The preprocessed frame, still 8-bit BGR.
        """
        preprocessor = ImagePreprocessor(frame)

        if self.config.resize_to is not None:
            width, height = self.config.resize_to
            preprocessor.resize(width, height)

        if self.config.apply_clahe:
            preprocessor.apply_clahe()

        return preprocessor.result()

    def process_frame(self, frame: np.ndarray) -> FrameOutcome:
        """Run one frame through the full pipeline.

        Stages run in the fixed order Camera → ImagePreprocessor →
        Detector → Tracker → RuleEngine. Detection, tracking, and rule
        coordinates all refer to the *preprocessed* frame, which is
        therefore the frame returned for rendering — drawing on the raw
        frame instead would misplace every box whenever resizing is on.

        Args:
            frame: The raw BGR frame from the camera.

        Returns:
            The frame's :class:`FrameOutcome`.
        """
        processed = self.preprocess(frame)

        height, width = processed.shape[:2]
        self._install_zones(width, height)

        detection_result = self.detector.detect(processed)
        tracked_objects = self.tracker.update(detection_result)
        rule_result = self.rule_engine.evaluate(
            tracked_objects=tracked_objects,
            frame_number=self.tracker.frame_number,
            frame_shape=(height, width),
        )

        return FrameOutcome(
            frame=processed,
            detection_result=detection_result,
            tracked_objects=tracked_objects,
            rule_result=rule_result,
        )

    def run(self) -> int:
        """Open the source and run the pipeline until the user quits.

        Returns:
            A process exit code: ``0`` on a clean shutdown, ``1`` if the
            video source could not be opened.
        """
        camera = Camera(source=self.config.source)

        try:
            camera.open()
        except CameraError as exc:
            logger.error(f"Cannot start pipeline: {exc}")
            return 1

        logger.info(
            f"Pipeline running on '{self.device}' with weights "
            f"'{self.config.weights}'. Active rules: "
            f"{', '.join(self.rule_engine.enabled_rule_names())}. "
            f"Press '{QUIT_KEY.upper()}' to quit."
        )

        consecutive_failures = 0

        try:
            while True:
                frame = camera.read()

                if frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= MAX_CONSECUTIVE_READ_FAILURES:
                        logger.warning(
                            f"No frame after {consecutive_failures} consecutive "
                            f"attempts; assuming the source has ended or "
                            f"disconnected. Stopping."
                        )
                        break
                    continue

                consecutive_failures = 0

                outcome = self.process_frame(frame)
                self.fps_counter.update()
                canvas = self.render(outcome)

                cv2.imshow(WINDOW_NAME, canvas)

                if cv2.waitKey(1) & 0xFF == ord(QUIT_KEY):
                    logger.info("Quit key pressed; shutting down pipeline.")
                    break
        except KeyboardInterrupt:
            logger.info("Interrupted by user; shutting down pipeline.")
        except Exception:
            logger.exception("Unexpected error in pipeline loop; shutting down.")
        finally:
            camera.release()
            cv2.destroyAllWindows()
            logger.info("Pipeline stopped; camera released and windows closed.")

        return 0

    def render(self, outcome: FrameOutcome) -> np.ndarray:
        """Draw the full overlay for one frame.

        Args:
            outcome: The frame's pipeline output.

        Returns:
            A new annotated frame; the input frame is left untouched.
        """
        canvas = outcome.frame.copy()
        severity_by_track = _severity_by_track(outcome.rule_result)

        _draw_zones(canvas, self.rule_engine.zones)
        _draw_tracks(canvas, outcome.tracked_objects, severity_by_track)
        _draw_hud(
            canvas,
            fps=self.fps_counter.get_fps(),
            device=self.device,
            model_name=self.detector.model_name,
            detection_count=len(outcome.detection_result),
            track_count=len(outcome.tracked_objects),
            rule_result=outcome.rule_result,
        )
        _draw_violations(
            canvas,
            rule_result=outcome.rule_result,
            max_lines=self.config.max_violation_lines,
        )
        return canvas


def _severity_by_track(rule_result: Optional[RuleResult]) -> Dict[int, Severity]:
    """Map each offending track to the worst severity it triggered.

    Args:
        rule_result: The frame's rule evaluation, if any.

    Returns:
        A ``{track_id: severity}`` lookup used to color boxes. Empty when
        there are no violations, or for scene-level violations that name
        no specific track.
    """
    severity_by_track: Dict[int, Severity] = {}

    if rule_result is None:
        return severity_by_track

    for violation in rule_result.violations:
        if violation.track_id is None:
            continue

        current = severity_by_track.get(violation.track_id)
        if current is None or violation.severity > current:
            severity_by_track[violation.track_id] = violation.severity

    return severity_by_track


def _draw_label(
    frame: np.ndarray,
    text: str,
    origin: Tuple[int, int],
    color: Tuple[int, int, int],
    scale: float = 0.5,
    thickness: int = 1,
) -> None:
    """Draw text on a filled background so it stays legible over video.

    Args:
        frame: The frame to draw on, modified in place.
        text: The text to render.
        origin: Bottom-left corner of the text, in pixels.
        color: BGR background color; the text itself is drawn in white.
        scale: Font scale factor.
        thickness: Text stroke thickness.
    """
    x, y = origin
    (text_width, text_height), baseline = cv2.getTextSize(text, FONT, scale, thickness)

    top = max(0, y - text_height - baseline - 2)
    cv2.rectangle(frame, (x, top), (x + text_width + 6, y), color, thickness=-1)
    cv2.putText(
        frame,
        text,
        (x + 3, y - baseline + 1),
        FONT,
        scale,
        COLOR_TEXT,
        thickness,
        cv2.LINE_AA,
    )


def _draw_zones(frame: np.ndarray, zones: Dict[str, Zone]) -> None:
    """Draw configured zones as translucent, labelled regions.

    Only rectangular zones are filled; other geometries are skipped
    rather than approximated, so nothing misleading is shown.

    Args:
        frame: The frame to draw on, modified in place.
        zones: The zones to draw, keyed by name.
    """
    if not zones:
        return

    overlay = frame.copy()

    for zone in zones.values():
        if not isinstance(zone, RectangleZone):
            continue

        color = COLOR_ZONE.get(zone.zone_type, COLOR_OK)
        top_left = (int(zone.x1), int(zone.y1))
        bottom_right = (int(zone.x2), int(zone.y2))
        cv2.rectangle(overlay, top_left, bottom_right, color, thickness=-1)

    cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, dst=frame)

    for zone in zones.values():
        if not isinstance(zone, RectangleZone):
            continue

        color = COLOR_ZONE.get(zone.zone_type, COLOR_OK)
        top_left = (int(zone.x1), int(zone.y1))
        bottom_right = (int(zone.x2), int(zone.y2))
        cv2.rectangle(frame, top_left, bottom_right, color, thickness=2)
        _draw_label(
            frame,
            f"{zone.name} [{zone.zone_type.value}]",
            (top_left[0], max(14, top_left[1] - 4)),
            color,
            scale=0.45,
        )


def _draw_tracks(
    frame: np.ndarray,
    tracked_objects: Sequence[TrackedObject],
    severity_by_track: Dict[int, Severity],
) -> None:
    """Draw each tracked object's box, identity, class, and confidence.

    Boxes are colored by the worst severity that object triggered, or
    green when it is compliant.

    Args:
        frame: The frame to draw on, modified in place.
        tracked_objects: The frame's tracked objects.
        severity_by_track: Worst severity per offending track.
    """
    for tracked_object in tracked_objects:
        x1, y1, x2, y2 = (int(value) for value in tracked_object.bounding_box.to_xyxy())

        severity = severity_by_track.get(tracked_object.track_id)
        color = COLOR_SEVERITY[severity] if severity is not None else COLOR_OK
        thickness = 3 if severity is not None else 2

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
        _draw_label(
            frame,
            f"#{tracked_object.track_id} {tracked_object.class_name} "
            f"{tracked_object.confidence:.2f}",
            (x1, max(14, y1 - 2)),
            color,
        )


def _draw_hud(
    frame: np.ndarray,
    fps: float,
    device: str,
    model_name: str,
    detection_count: int,
    track_count: int,
    rule_result: Optional[RuleResult],
) -> None:
    """Draw the status bar along the top of the frame.

    Args:
        frame: The frame to draw on, modified in place.
        fps: Current frames-per-second estimate.
        device: The compute device in use.
        model_name: Identifier of the loaded weights.
        detection_count: Raw detections in this frame.
        track_count: Confirmed tracks in this frame.
        rule_result: The frame's rule evaluation, if any.
    """
    height, width = frame.shape[:2]
    bar_height = 30

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, bar_height), COLOR_PANEL, thickness=-1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, dst=frame)

    violation_count = len(rule_result) if rule_result is not None else 0
    status_color = COLOR_OK if violation_count == 0 else COLOR_SEVERITY[
        rule_result.highest_severity if rule_result and rule_result.highest_severity
        else Severity.MEDIUM
    ]

    left_text = (
        f"FPS {fps:5.1f} | {device.upper()} | {model_name} | "
        f"det {detection_count} | trk {track_count}"
    )
    cv2.putText(frame, left_text, (8, 20), FONT, 0.5, COLOR_TEXT, 1, cv2.LINE_AA)

    status = "SAFE" if violation_count == 0 else f"VIOLATIONS: {violation_count}"
    (status_width, _), _ = cv2.getTextSize(status, FONT, 0.6, 2)
    cv2.putText(
        frame,
        status,
        (max(8, width - status_width - 10), 21),
        FONT,
        0.6,
        status_color,
        2,
        cv2.LINE_AA,
    )


def _draw_violations(
    frame: np.ndarray,
    rule_result: Optional[RuleResult],
    max_lines: int = 5,
) -> None:
    """List the frame's active violations, most severe first.

    Args:
        frame: The frame to draw on, modified in place.
        rule_result: The frame's rule evaluation, if any.
        max_lines: Maximum violations to list before summarizing the rest.
    """
    if rule_result is None or rule_result.is_safe:
        return

    violations = rule_result.by_severity(Severity.INFO)[:max_lines]
    overflow = len(rule_result) - len(violations)

    line_height = 20
    panel_height = line_height * (len(violations) + (1 if overflow > 0 else 0)) + 10
    top = frame.shape[0] - panel_height

    overlay = frame.copy()
    cv2.rectangle(
        overlay, (0, top), (frame.shape[1], frame.shape[0]), COLOR_PANEL, thickness=-1
    )
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, dst=frame)

    for index, violation in enumerate(violations):
        y = top + 18 + index * line_height
        color = COLOR_SEVERITY.get(violation.severity, COLOR_OK)
        cv2.circle(frame, (12, y - 5), 5, color, thickness=-1)
        cv2.putText(
            frame,
            f"[{str(violation.severity).upper()}] {violation.description}",
            (26, y),
            FONT,
            0.45,
            COLOR_TEXT,
            1,
            cv2.LINE_AA,
        )

    if overflow > 0:
        y = top + 18 + len(violations) * line_height
        cv2.putText(
            frame,
            f"... and {overflow} more",
            (26, y),
            FONT,
            0.45,
            COLOR_TEXT,
            1,
            cv2.LINE_AA,
        )


def _parse_source(value: str) -> Union[int, str]:
    """Interpret a ``--source`` argument as a webcam index or a file path.

    Args:
        value: The raw command-line value.

    Returns:
        An ``int`` webcam index when the value is numeric, otherwise the
        value unchanged as a path.
    """
    try:
        return int(value)
    except ValueError:
        return value


def _parse_resize(value: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse a ``WIDTHxHEIGHT`` argument into a dimensions tuple.

    Args:
        value: The raw command-line value, e.g. ``"640x480"``, or ``None``.

    Returns:
        The ``(width, height)`` tuple, or ``None`` if no value was given.

    Raises:
        argparse.ArgumentTypeError: If the value is malformed or non-positive.
    """
    if value is None:
        return None

    try:
        width_text, height_text = value.lower().split("x")
        width, height = int(width_text), int(height_text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Expected resize in WIDTHxHEIGHT form (e.g. 640x480), got '{value}'"
        ) from None

    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError(
            f"Resize dimensions must be positive, got {width}x{height}"
        )

    return width, height


def parse_args(argv: Optional[Sequence[str]] = None) -> PipelineConfig:
    """Parse command-line arguments into a :class:`PipelineConfig`.

    Args:
        argv: Argument list to parse. Defaults to ``sys.argv[1:]``.

    Returns:
        The resulting configuration.
    """
    parser = argparse.ArgumentParser(
        description="Run the end-to-end AI warehouse safety inspection pipeline.",
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Webcam index or path to a video file (default: 0).",
    )
    parser.add_argument(
        "--weights",
        default="yolov8n.pt",
        help="YOLO weights path or built-in model name (default: yolov8n.pt).",
    )
    parser.add_argument(
        "--device",
        choices=("cuda", "cpu"),
        default=None,
        help="Compute device. Defaults to CUDA when available, else CPU.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Detection confidence threshold (default: 0.25).",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.45,
        help="NMS IoU threshold (default: 0.45).",
    )
    parser.add_argument(
        "--resize",
        default=None,
        help="Resize frames before inference, as WIDTHxHEIGHT (e.g. 640x480).",
    )
    parser.add_argument(
        "--no-clahe",
        action="store_true",
        help="Disable CLAHE contrast enhancement.",
    )
    parser.add_argument(
        "--no-zones",
        action="store_true",
        help="Do not install the demonstration safety zones.",
    )
    parser.add_argument(
        "--frame-rate",
        type=int,
        default=30,
        help="Expected source frame rate, used to size the tracker buffer (default: 30).",
    )

    args = parser.parse_args(argv)

    return PipelineConfig(
        source=_parse_source(args.source),
        weights=args.weights,
        device=args.device,
        confidence_threshold=args.conf,
        iou_threshold=args.iou,
        resize_to=_parse_resize(args.resize),
        apply_clahe=not args.no_clahe,
        enable_zones=not args.no_zones,
        frame_rate=args.frame_rate,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Build and run the pipeline.

    Args:
        argv: Argument list to parse. Defaults to ``sys.argv[1:]``.

    Returns:
        A process exit code.
    """
    config = parse_args(argv)
    logger.info(f"Starting {settings.app_name} v{settings.app_version} pipeline.")

    try:
        pipeline = SafetyPipeline(config)
    except ModelLoadError as exc:
        logger.error(f"Cannot load detection model: {exc}")
        return 1
    except TrackerInitializationError as exc:
        logger.error(f"Cannot initialize tracker: {exc}")
        return 1
    except ValueError as exc:
        logger.error(f"Invalid pipeline configuration: {exc}")
        return 1

    return pipeline.run()


if __name__ == "__main__":
    sys.exit(main())
