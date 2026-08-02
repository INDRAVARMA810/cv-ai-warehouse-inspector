"""YOLO model loading, device selection, and in-process model caching.

This module is the single place responsible for turning a weights path
into a ready-to-use Ultralytics ``YOLO`` model instance: choosing the
best available compute device (CUDA if available, otherwise CPU),
falling back safely if an unavailable device is requested, and
avoiding redundant reloads of the same weights.

Loading anything other than weights/device concerns (inference,
thresholds, result parsing) is intentionally out of scope here — see
:mod:`app.detection.yolo_engine`.
"""

from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional, Union

from app.logger import logger

try:
    import torch
    from ultralytics import YOLO
except ImportError as exc:  # ultralytics/torch are optional until inference is needed
    torch = None  # type: ignore[assignment]
    YOLO = None  # type: ignore[assignment]
    _IMPORT_ERROR: Optional[ImportError] = exc
else:
    _IMPORT_ERROR = None


class ModelLoadError(Exception):
    """Raised when a YOLO model cannot be loaded."""


# Process-wide cache of loaded models, keyed by "<weights_path>:<device>".
_MODEL_CACHE: Dict[str, Any] = {}
_CACHE_LOCK = Lock()


def get_best_device() -> str:
    """Determine the best available compute device.

    Returns:
        ``"cuda"`` if PyTorch was built with CUDA support and a
        CUDA-capable GPU is available, otherwise ``"cpu"``.
    """
    if torch is not None and torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _resolve_device(requested: Optional[str]) -> str:
    """Resolve a requested device against actual availability.

    Args:
        requested: The caller's preferred device, or ``None`` to select
            automatically.

    Returns:
        ``"cuda"`` or ``"cpu"``, with an automatic fallback to CPU if
        CUDA was requested but is not actually available.
    """
    if requested is None:
        return get_best_device()

    if requested == "cuda" and get_best_device() != "cuda":
        logger.warning("CUDA requested but not available; falling back to CPU.")
        return "cpu"

    return requested


def load_model(weights_path: Union[str, Path], device: Optional[str] = None) -> Any:
    """Load (or retrieve from cache) an Ultralytics YOLO model.

    Args:
        weights_path: Path to a ``.pt`` weights file — either a
            built-in Ultralytics model name (e.g. ``"yolov8n.pt"``) or
            a path to custom-trained weights.
        device: Compute device to load the model onto (``"cuda"`` or
            ``"cpu"``). If ``None``, the best available device is
            selected automatically.

    Returns:
        A ready-to-use ``ultralytics.YOLO`` model instance, moved to
        the resolved device.

    Raises:
        ModelLoadError: If the ``ultralytics``/``torch`` dependencies
            are not installed, or the weights fail to load.
    """
    if YOLO is None or torch is None:
        raise ModelLoadError(
            "ultralytics/torch are not installed. Install them with "
            "`pip install ultralytics torch` to enable YOLO detection."
        ) from _IMPORT_ERROR

    resolved_device = _resolve_device(device)
    cache_key = f"{weights_path}:{resolved_device}"

    with _CACHE_LOCK:
        cached_model = _MODEL_CACHE.get(cache_key)
        if cached_model is not None:
            logger.debug(f"Using cached YOLO model: {cache_key}")
            return cached_model

        logger.info(f"Loading YOLO model '{weights_path}' on device '{resolved_device}'...")

        try:
            model = YOLO(str(weights_path))
            model.to(resolved_device)
        except Exception as exc:
            raise ModelLoadError(
                f"Failed to load YOLO weights from '{weights_path}': {exc}"
            ) from exc

        _MODEL_CACHE[cache_key] = model
        logger.info(f"YOLO model ready: '{weights_path}' on '{resolved_device}'.")
        return model


def clear_cache() -> None:
    """Clear all cached model instances.

    Useful for tests, or when reloading updated weights under the same
    path during a long-running process.
    """
    with _CACHE_LOCK:
        _MODEL_CACHE.clear()
        logger.debug("YOLO model cache cleared.")
