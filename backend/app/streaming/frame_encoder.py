"""JPEG encoding for video frames.

Converts the annotated BGR frames produced by the detection pipeline
into JPEG bytes suitable for an MJPEG stream.

Encoding is the single most expensive step in the streaming path after
inference, so the encoder is deliberately small and stateless: callers
can share one instance across threads, and the caching that avoids
re-encoding the same frame for every viewer lives in
:class:`~app.streaming.stream_manager.StreamManager`.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np

from app.logger import logger


class EncodingError(Exception):
    """Raised when a frame cannot be encoded to JPEG."""


@dataclass
class EncoderConfig:
    """Tuning parameters for :class:`FrameEncoder`.

    Attributes:
        quality: JPEG quality in ``1..100``. Around 70–80 is the usual
            sweet spot for surveillance imagery: below ~60 compression
            artefacts start to obscure the small, distant objects a
            safety operator needs to see, while above ~85 the bitrate
            roughly doubles for no perceptible benefit.
        max_width: Downscale frames wider than this before encoding.
            ``None`` keeps the native width. Streaming a 1080p feed to a
            dashboard panel wastes bandwidth on pixels the browser will
            immediately scale away.
        progressive: Whether to emit progressive JPEG. Slightly smaller,
            but not every decoder handles it well inside a multipart
            stream, so it is off by default.
    """

    quality: int = 75
    max_width: Optional[int] = 1280
    progressive: bool = False

    def __post_init__(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If quality is outside ``1..100`` or ``max_width``
                is not positive.
        """
        if not 1 <= self.quality <= 100:
            raise ValueError(f"quality must be in 1..100, got {self.quality}")

        if self.max_width is not None and self.max_width <= 0:
            raise ValueError(f"max_width must be positive, got {self.max_width}")


class FrameEncoder:
    """Encodes BGR frames as JPEG bytes.

    Instances are stateless apart from their configuration, so a single
    encoder can safely be shared between threads.

    Attributes:
        config: The encoding parameters in effect.
    """

    def __init__(self, config: Optional[EncoderConfig] = None) -> None:
        """Configure the encoder.

        Args:
            config: Encoding parameters. Defaults to
                :class:`EncoderConfig`.
        """
        self.config = config or EncoderConfig()

    @property
    def quality(self) -> int:
        """Current JPEG quality."""
        return self.config.quality

    @quality.setter
    def quality(self, value: int) -> None:
        """Set JPEG quality at runtime.

        Args:
            value: New quality, in ``1..100``.

        Raises:
            ValueError: If the value is out of range.
        """
        if not 1 <= value <= 100:
            raise ValueError(f"quality must be in 1..100, got {value}")

        self.config.quality = value
        logger.info(f"Stream JPEG quality set to {value}.")

    def _encode_params(self) -> list:
        """Build the OpenCV imencode parameter list.

        Returns:
            Flat ``[flag, value, ...]`` parameters.
        """
        params = [cv2.IMWRITE_JPEG_QUALITY, self.config.quality]

        if self.config.progressive:
            params += [cv2.IMWRITE_JPEG_PROGRESSIVE, 1]

        return params

    def _fit_width(self, frame: np.ndarray) -> np.ndarray:
        """Downscale a frame to the configured maximum width.

        Only ever shrinks: upscaling would cost bandwidth without adding
        any detail.

        Args:
            frame: The frame to resize.

        Returns:
            The resized frame, or the original if no resize was needed.
        """
        max_width = self.config.max_width
        if max_width is None:
            return frame

        height, width = frame.shape[:2]
        if width <= max_width:
            return frame

        scale = max_width / float(width)
        target = (max_width, max(1, int(round(height * scale))))

        # INTER_AREA is the correct choice for downscaling; it averages
        # source pixels instead of sampling them, which avoids the
        # aliasing that would shimmer badly in a moving video stream.
        return cv2.resize(frame, target, interpolation=cv2.INTER_AREA)

    def encode(self, frame: np.ndarray) -> bytes:
        """Encode a BGR frame as JPEG.

        Args:
            frame: The frame to encode, in OpenCV's native BGR order.

        Returns:
            The encoded JPEG bytes.

        Raises:
            ValueError: If the frame is empty or not a NumPy array.
            EncodingError: If OpenCV fails to encode the frame.
        """
        if not isinstance(frame, np.ndarray):
            raise ValueError(f"frame must be a numpy array, got {type(frame).__name__}")

        if frame.size == 0:
            raise ValueError("frame must not be empty")

        prepared = self._fit_width(frame)

        success, buffer = cv2.imencode(".jpg", prepared, self._encode_params())

        if not success:
            raise EncodingError("cv2.imencode() failed to encode the frame as JPEG")

        return buffer.tobytes()

    def encode_safe(self, frame: np.ndarray) -> Optional[bytes]:
        """Encode a frame, returning ``None`` instead of raising.

        Intended for the streaming loop, where a single bad frame should
        be skipped rather than tearing down every viewer's connection.

        Args:
            frame: The frame to encode.

        Returns:
            The encoded JPEG bytes, or ``None`` if encoding failed.
        """
        try:
            return self.encode(frame)
        except (ValueError, EncodingError) as exc:
            logger.warning(f"Skipping frame that could not be encoded: {exc}")
            return None

    def encoded_size(self, frame: np.ndarray) -> Tuple[int, int]:
        """Report the encoded size of a frame, for diagnostics.

        Args:
            frame: The frame to measure.

        Returns:
            An ``(encoded_bytes, quality)`` tuple.
        """
        return len(self.encode(frame)), self.config.quality
