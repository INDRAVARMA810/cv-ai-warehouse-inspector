"""Camera and video-file capture abstraction built on OpenCV.

Provides a small, safe wrapper around :class:`cv2.VideoCapture` for
reading frames from a webcam or a video file, with graceful handling
of invalid sources and guaranteed resource release.
"""

from types import TracebackType
from typing import Optional, Type, Union

import cv2
import numpy as np

from app.logger import logger


class CameraError(Exception):
    """Raised when a camera or video source cannot be opened or read."""


class Camera:
    """Wraps a :class:`cv2.VideoCapture` source (webcam or video file).

    Supports use as a context manager, guaranteeing that the underlying
    capture device is released even if an error occurs while reading.

    Attributes:
        source: Webcam index (e.g. ``0``) or a path/URL to a video file.
    """

    def __init__(self, source: Union[int, str] = 0) -> None:
        """Initialize the camera wrapper without opening the source.

        Args:
            source: Webcam device index (``int``) or a path/URL to a
                video file (``str``). Defaults to ``0`` (default webcam).
        """
        self.source: Union[int, str] = source
        self._capture: Optional[cv2.VideoCapture] = None

    def open(self) -> None:
        """Open the underlying video source.

        Raises:
            CameraError: If the source cannot be opened (e.g. an
                invalid webcam index or a missing/corrupt video file).
        """
        capture = cv2.VideoCapture(self.source)

        if not capture.isOpened():
            capture.release()
            raise CameraError(f"Unable to open video source: {self.source!r}")

        self._capture = capture
        logger.info(f"Camera source opened: {self.source!r}")

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
