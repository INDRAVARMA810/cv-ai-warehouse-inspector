"""Reusable frame post-processing utilities for the video pipeline.

Provides :class:`VideoReader`, which applies common frame
transformations — resizing and color space conversion — independent of
where the frame originated (webcam or video file).
"""

from typing import Optional, Tuple

import cv2
import numpy as np


class VideoReader:
    """Applies reusable processing steps to raw video frames.

    Attributes:
        resize_dims: Target ``(width, height)`` to resize frames to,
            or ``None`` to leave frames at their original size.
        convert_to_rgb: Whether processed frames should be converted
            from OpenCV's native BGR channel order to RGB.
    """

    def __init__(
        self,
        resize_dims: Optional[Tuple[int, int]] = None,
        convert_to_rgb: bool = False,
    ) -> None:
        """Initialize the reader with fixed processing options.

        Args:
            resize_dims: Optional ``(width, height)`` to resize frames to.
            convert_to_rgb: If ``True``, converts frames from BGR to RGB.
        """
        self.resize_dims = resize_dims
        self.convert_to_rgb = convert_to_rgb

    def resize(self, frame: np.ndarray, width: int, height: int) -> np.ndarray:
        """Resize a frame to the given pixel dimensions.

        Args:
            frame: Input frame.
            width: Target width, in pixels.
            height: Target height, in pixels.

        Returns:
            The resized frame.
        """
        return cv2.resize(frame, (width, height), interpolation=cv2.INTER_LINEAR)

    def convert_color(self, frame: np.ndarray, conversion: int) -> np.ndarray:
        """Convert a frame between color spaces.

        Args:
            frame: Input frame.
            conversion: An OpenCV color conversion code, e.g.
                ``cv2.COLOR_BGR2RGB``.

        Returns:
            The color-converted frame.
        """
        return cv2.cvtColor(frame, conversion)

    def process(self, frame: np.ndarray) -> np.ndarray:
        """Apply the configured resize and color conversion to a frame.

        Args:
            frame: Raw input frame, in BGR order as produced by OpenCV.

        Returns:
            The processed frame.
        """
        processed = frame

        if self.resize_dims is not None:
            width, height = self.resize_dims
            processed = self.resize(processed, width, height)

        if self.convert_to_rgb:
            processed = self.convert_color(processed, cv2.COLOR_BGR2RGB)

        return processed
