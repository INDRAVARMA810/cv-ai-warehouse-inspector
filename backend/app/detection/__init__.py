"""YOLO-based object detection engine.

Provides a modular detection architecture: a low-level model loader
(:mod:`app.detection.model_loader`), a model-specific inference engine
(:class:`YOLOEngine`), a high-level orchestration class
(:class:`Detector`), and model-agnostic result dataclasses. The split
between ``YOLOEngine`` and ``Detector`` exists so additional detector
backends can be introduced later without changing the public
:class:`Detector` interface.
"""

from app.detection.detection_result import BoundingBox, Detection, DetectionResult
from app.detection.detector import Detector
from app.detection.model_loader import ModelLoadError
from app.detection.yolo_engine import InferenceError, YOLOEngine

__all__ = [
    "Detector",
    "YOLOEngine",
    "BoundingBox",
    "Detection",
    "DetectionResult",
    "ModelLoadError",
    "InferenceError",
]
