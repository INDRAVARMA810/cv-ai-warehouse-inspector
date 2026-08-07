"""Camera and video-file capture abstraction built on OpenCV.

Provides a small, safe wrapper around :class:`cv2.VideoCapture` for
reading frames from a webcam or a video file, with graceful handling
of invalid sources and guaranteed resource release.
"""

import os
import platform
from types import TracebackType
from typing import Optional, Type, Union

import cv2
import numpy as np

from app.logger import logger


class CameraError(Exception):
    """Raised when a camera or video source cannot be opened or read."""


def _resolve_backend(name: str, source: Union[int, str]) -> int:
    """Map a ``CAMERA_BACKEND`` value to an OpenCV ``VideoCapture`` API preference.

    ``dshow``/``msmf`` are Windows camera-capture APIs; they cannot open a
    video file or URL, so they only apply when ``source`` is a webcam index.
    For anything else (file paths, streams, non-Windows platforms) this
    resolves to ``cv2.CAP_ANY``, OpenCV's own auto-detection — the same
    backend selection :class:`Camera` used before this option existed.

    Args:
        name: ``"auto"``, ``"dshow"``, or ``"msmf"`` (case-insensitive).
        source: The capture source, used to tell a webcam index apart
            from a file/URL source.

    Returns:
        An OpenCV ``cv2.CAP_*`` constant to pass as the ``apiPreference``
        argument of :class:`cv2.VideoCapture`.
    """
    normalized = (name or "auto").strip().lower()

    if not isinstance(source, int):
        if normalized not in ("auto", ""):
            logger.warning(
                f"CAMERA_BACKEND={name!r} only applies to webcam indices; "
                f"ignoring it for file/URL source {source!r}."
            )
        return cv2.CAP_ANY

    if normalized == "dshow":
        return cv2.CAP_DSHOW
    if normalized == "msmf":
        return cv2.CAP_MSMF
    if normalized != "auto":
        logger.warning(f"Unknown CAMERA_BACKEND={name!r}; falling back to 'auto'.")

    # Auto: MSMF (OpenCV's own default on Windows) is the backend that was
    # failing to grab frames; DirectShow is the long-standing reliable
    # alternative. Linux/macOS keep CAP_ANY, i.e. no behavior change there.
    return cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY


class Camera:
    """Wraps a :class:`cv2.VideoCapture` source (webcam or video file).

    Supports use as a context manager, guaranteeing that the underlying
    capture device is released even if an error occurs while reading.

    Attributes:
        source: Webcam index (e.g. ``0``) or a path/URL to a video file.
        backend: Requested capture backend (``"auto"``, ``"dshow"``, or
            ``"msmf"``).
    """

    def __init__(self, source: Union[int, str] = 0, backend: Optional[str] = None) -> None:
        """Initialize the camera wrapper without opening the source.

        Args:
            source: Webcam device index (``int``) or a path/URL to a
                video file (``str``). Defaults to ``0`` (default webcam).
            backend: Capture backend to use: ``"auto"`` (default), ``"dshow"``,
                or ``"msmf"``. When omitted, falls back to the
                ``CAMERA_BACKEND`` environment variable, then ``"auto"``.
        """
        self.source: Union[int, str] = source
        self.backend: str = backend if backend is not None else os.getenv("CAMERA_BACKEND", "auto")
        self._api_preference: int = _resolve_backend(self.backend, source)
        self._capture: Optional[cv2.VideoCapture] = None

    def open(self) -> None:
        """Open the underlying video source.

        Raises:
            CameraError: If the source cannot be opened (e.g. an
                invalid webcam index or a missing/corrupt video file).
        """
        capture = cv2.VideoCapture(self.source, self._api_preference)

        if not capture.isOpened():
            capture.release()
            raise CameraError(f"Unable to open video source: {self.source!r}")

        self._capture = capture
        logger.info(f"Camera source opened: {self.source!r} (backend={self.backend})")

    def is_opened(self) -> bool:
        """Return whether the video source is currently open."""
        return self._capture is not None and self._capture.isOpened()

    def read(self) -> Optional[np.ndarray]:
        """Read a single frame from the video source.

        Returns:
            The captured frame as a BGR ``numpy.ndarray``, or ``None``
            if no frame could be read (e.g. end of a video file, a
            dropped webcam frame, or the source is not open).
        """
        if not self.is_opened():
            logger.warning("Attempted to read from a closed camera source.")
            return None

        success, frame = self._capture.read()  # type: ignore[union-attr]

        if not success or frame is None:
            logger.warning(f"Failed to read frame from source: {self.source!r}")
            return None

        return frame

    def release(self) -> None:
        """Release the underlying video source, if currently open.

        Safe to call multiple times.
        """
        if self._capture is not None:
            self._capture.release()
            logger.info(f"Camera source released: {self.source!r}")
            self._capture = None

    def __enter__(self) -> "Camera":
        """Open the camera source and return ``self`` for a ``with`` block."""
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Guarantee the camera source is released when leaving a ``with`` block."""
        self.release()
