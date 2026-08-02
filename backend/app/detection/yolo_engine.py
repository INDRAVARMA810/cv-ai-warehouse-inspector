"""Ultralytics YOLO inference engine.

Wraps a loaded YOLO model to provide a narrow, model-specific
inference interface: given a frame, return a list of structured
:class:`Detection` objects. Contains no drawing, tracking, or
higher-level orchestration logic — see :mod:`app.detection.detector`
for that.
"""

from pathlib import Path
from typing import Any, List, Optional, Union

import numpy as np

from app.detection.detection_result import BoundingBox, Detection
from app.detection.model_loader import load_model
from app.logger import logger


class InferenceError(Exception):
    """Raised when YOLO inference fails on a given frame."""


class YOLOEngine:
    """Runs object detection inference using an Ultralytics YOLO model.

    Attributes:
        weights_path: Path (or built-in name) of the loaded weights.
        device: Compute device the model is running on.
    """

    def __init__(
        self,
        weights_path: Union[str, Path],
        device: Optional[str] = None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ) -> None:
        """Load a YOLO model and configure inference parameters.

        Args:
            weights_path: Path to a ``.pt`` weights file, or a
                built-in Ultralytics model name (e.g. ``"yolov8n.pt"``).
            device: Compute device to run on (``"cuda"`` or ``"cpu"``).
                If ``None``, the best available device is chosen
                automatically, with automatic CPU fallback.
            confidence_threshold: Minimum confidence score, in
                ``[0, 1]``, for a detection to be returned.
            iou_threshold: IoU threshold, in ``[0, 1]``, used during
                non-max suppression.

        Raises:
            ValueError: If either threshold is outside ``[0, 1]``.
            ModelLoadError: If the model fails to load.
        """
        self.weights_path = weights_path
        self._model = load_model(weights_path, device=device)
        self.device = str(getattr(self._model, "device", device or "cpu"))

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold

        logger.info(
            f"YOLOEngine ready: weights='{weights_path}', device='{self.device}', "
            f"confidence>={self.confidence_threshold}, iou={self.iou_threshold}"
        )

    @property
    def confidence_threshold(self) -> float:
        """Minimum confidence score, in ``[0, 1]``, for a kept detection."""
        return self._confidence_threshold

    @confidence_threshold.setter
    def confidence_threshold(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"confidence_threshold must be in [0, 1], got {value}")
        self._confidence_threshold = value

    @property
    def iou_threshold(self) -> float:
        """IoU threshold, in ``[0, 1]``, used for non-max suppression."""
        return self._iou_threshold

    @iou_threshold.setter
    def iou_threshold(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"iou_threshold must be in [0, 1], got {value}")
        self._iou_threshold = value

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run inference on a single frame.

        Args:
            frame: Input image in BGR order, as produced by OpenCV.

        Returns:
            A list of :class:`Detection` objects, one per object found
            above ``confidence_threshold``. Empty if nothing was
            detected.

        Raises:
            ValueError: If ``frame`` is ``None`` or empty.
            InferenceError: If the underlying model fails to run.
        """
        if frame is None or frame.size == 0:
            raise ValueError("frame must be a non-empty numpy array")

        try:
            results = self._model.predict(
                source=frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:
            raise InferenceError(f"YOLO inference failed: {exc}") from exc

        return self._parse_results(results)

    def _parse_results(self, results: Any) -> List[Detection]:
        """Convert raw Ultralytics results into :class:`Detection` objects.

        Args:
            results: The list-like result object returned by
                ``YOLO.predict``.

        Returns:
            The parsed list of detections.
        """
        detections: List[Detection] = []

        if not results:
            return detections

        result = results[0]
        boxes = getattr(result, "boxes", None)

        if boxes is None or len(boxes) == 0:
            return detections

        class_names = result.names

        for box in boxes:
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            class_name = self._resolve_class_name(class_names, class_id)

            detections.append(
                Detection(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    bounding_box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                )
            )

        return detections

    @staticmethod
    def _resolve_class_name(class_names: Any, class_id: int) -> str:
        """Look up a class name, tolerating dict- or list-style name maps.

        Args:
            class_names: The model's class name mapping (``dict[int, str]``
                or a list of names, depending on Ultralytics version).
            class_id: The class index to resolve.

        Returns:
            The resolved class name, or the stringified ``class_id`` if
            it cannot be found.
        """
        if isinstance(class_names, dict):
            return class_names.get(class_id, str(class_id))

        if 0 <= class_id < len(class_names):
            return class_names[class_id]

        return str(class_id)
