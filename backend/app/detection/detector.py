"""High-level detection orchestration.

Provides :class:`Detector`, the single entry point the rest of the
application should use to run object detection on a frame. It owns no
model-specific logic itself — that lives in
:mod:`app.detection.yolo_engine` — so the underlying engine can be
swapped out in the future without changing this interface.
"""

import time
from pathlib import Path
from typing import Optional, Union

import numpy as np

from app.detection.detection_result import DetectionResult
from app.detection.yolo_engine import InferenceError, YOLOEngine
from app.logger import logger


class Detector:
    """Runs object detection on frames and returns structured results.

    Attributes:
        model_name: Identifier of the underlying model's weights.
    """

    def __init__(
        self,
        weights_path: Union[str, Path],
        device: Optional[str] = None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> None:
        """Configure the detector and load its underlying engine.

        Args:
            weights_path: Path to a ``.pt`` weights file, or a
                built-in Ultralytics model name (e.g. ``"yolov8n.pt"``).
            device: Compute device to run on (``"cuda"`` or ``"cpu"``).
                If ``None``, the best available device is chosen
                automatically, with automatic CPU fallback.
            confidence_threshold: Minimum confidence score, in
                ``[0, 1]``, for a detection to be kept.
            iou_threshold: IoU threshold, in ``[0, 1]``, used during
                non-max suppression.

        Raises:
            ValueError: If either threshold is outside ``[0, 1]``.
            ModelLoadError: If the underlying model fails to load.
        """
        self.model_name = str(weights_path)
        self._engine = YOLOEngine(
            weights_path=weights_path,
            device=device,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
        )

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Run detection on a single processed frame.

        Args:
            frame: Input image in BGR order, typically already resized
                and cleaned up by :mod:`app.image_processing`.

        Returns:
            A :class:`DetectionResult` describing everything found in
            the frame. If ``frame`` is empty or inference fails, an
            empty result is returned rather than raising, so a single
            bad frame does not interrupt a video pipeline.
        """
        if frame is None or frame.size == 0:
            logger.warning("Detector.detect() received an empty frame; skipping.")
            return DetectionResult(model_name=self.model_name)

        start_time = time.perf_counter()

        try:
            detections = self._engine.detect(frame)
        except InferenceError as exc:
            logger.error(f"Detection failed for current frame: {exc}")
            detections = []

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        height, width = frame.shape[:2]

        result = DetectionResult(
            detections=detections,
            frame_shape=(height, width),
            model_name=self.model_name,
            inference_time_ms=elapsed_ms,
        )

        logger.debug(
            f"Detector found {len(detections)} object(s) in {elapsed_ms:.1f} ms."
        )
        return result
