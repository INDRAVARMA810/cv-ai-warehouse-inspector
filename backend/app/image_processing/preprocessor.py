"""Chainable image preprocessing pipeline built on OpenCV.

Provides :class:`ImagePreprocessor`, a fluent-interface wrapper around a
single image that supports composing multiple preprocessing operations
(resize, color conversion, normalization, filtering, and contrast
enhancement) into a single readable call chain.
"""

from typing import Tuple

import cv2
import numpy as np

from app.logger import logger


class ImagePreprocessor:
    """Applies a chainable sequence of preprocessing operations to an image.

    Each method mutates the internally held image and returns ``self``,
    allowing operations to be composed fluently::

        result = (
            ImagePreprocessor(frame)
            .resize(640, 480)
            .apply_clahe()
            .to_rgb()
            .normalize()
            .result()
        )

    Operations are applied in the order they are called; some
    combinations are order-sensitive (e.g. ``normalize`` produces a
    float image, so it should typically be called last).

    Attributes:
        image: The current, possibly transformed, image.
    """

    def __init__(self, image: np.ndarray) -> None:
        """Initialize the pipeline with a source image.

        Args:
            image: The image to process, as a ``numpy.ndarray`` (BGR or
                grayscale, as produced by OpenCV).

        Raises:
            TypeError: If ``image`` is not a ``numpy.ndarray``.
        """
        if not isinstance(image, np.ndarray):
            raise TypeError(f"Expected a numpy.ndarray, got {type(image).__name__}")

        self.image: np.ndarray = image

    def resize(
        self,
        width: int,
        height: int,
        interpolation: int = cv2.INTER_LINEAR,
    ) -> "ImagePreprocessor":
        """Resize the image to the given pixel dimensions.

        Args:
            width: Target width, in pixels.
            height: Target height, in pixels.
            interpolation: OpenCV interpolation flag.

        Returns:
            ``self``, for chaining.
        """
        self.image = cv2.resize(
            self.image, (width, height), interpolation=interpolation
        )
        return self

    def normalize(self, alpha: float = 0.0, beta: float = 1.0) -> "ImagePreprocessor":
        """Min-max normalize pixel values into the ``[alpha, beta]`` range.

        Converts the image to ``float32`` in the process. This is
        typically the last operation in a pipeline feeding a model.

        Args:
            alpha: Lower bound of the target range.
            beta: Upper bound of the target range.

        Returns:
            ``self``, for chaining.
        """
        float_image = self.image.astype(np.float32)
        self.image = cv2.normalize(
            float_image, None, alpha=alpha, beta=beta, norm_type=cv2.NORM_MINMAX
        )
        return self

    def to_rgb(self) -> "ImagePreprocessor":
        """Convert the image from BGR to RGB channel order.

        No-op (with a warning) if the image is already single-channel.

        Returns:
            ``self``, for chaining.
        """
        if self.image.ndim != 3:
            logger.warning("to_rgb() skipped: image is not a 3-channel color image.")
            return self

        self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        return self

    def to_bgr(self) -> "ImagePreprocessor":
        """Convert the image from RGB to BGR channel order.

        No-op (with a warning) if the image is already single-channel.

        Returns:
            ``self``, for chaining.
        """
        if self.image.ndim != 3:
            logger.warning("to_bgr() skipped: image is not a 3-channel color image.")
            return self

        self.image = cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR)
        return self

    def to_grayscale(self) -> "ImagePreprocessor":
        """Convert the image to single-channel grayscale.

        No-op if the image is already grayscale.

        Returns:
            ``self``, for chaining.
        """
        if self.image.ndim == 3:
            self.image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        return self

    def gaussian_blur(
        self,
        kernel_size: Tuple[int, int] = (5, 5),
        sigma: float = 0.0,
    ) -> "ImagePreprocessor":
        """Apply Gaussian blur to the image.

        Args:
            kernel_size: ``(width, height)`` of the Gaussian kernel; both
                values must be positive and odd.
            sigma: Gaussian kernel standard deviation. ``0`` derives it
                automatically from the kernel size.

        Returns:
            ``self``, for chaining.

        Raises:
            ValueError: If either kernel dimension is not a positive odd
                integer.
        """
        if any(dim <= 0 or dim % 2 == 0 for dim in kernel_size):
            raise ValueError(f"kernel_size must contain positive odd integers, got {kernel_size}")

        self.image = cv2.GaussianBlur(self.image, kernel_size, sigma)
        return self

    def equalize_histogram(self) -> "ImagePreprocessor":
        """Apply global histogram equalization to improve contrast.

        For grayscale images, equalization is applied directly. For
        color images, equalization is applied to the luminance (Y)
        channel in YCrCb space, preserving color balance.

        Returns:
            ``self``, for chaining.
        """
        if self.image.ndim == 2:
            self.image = cv2.equalizeHist(self.image)
            return self

        ycrcb = cv2.cvtColor(self.image, cv2.COLOR_BGR2YCrCb)
        ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
        self.image = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
        return self

    def apply_clahe(
        self,
        clip_limit: float = 2.0,
        tile_grid_size: Tuple[int, int] = (8, 8),
    ) -> "ImagePreprocessor":
        """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).

        For grayscale images, CLAHE is applied directly. For color
        images, it is applied to the lightness (L) channel in LAB
        space, preserving color balance.

        Args:
            clip_limit: Threshold for contrast limiting.
            tile_grid_size: Number of tiles in the ``(columns, rows)``
                grid used for local histogram equalization.

        Returns:
            ``self``, for chaining.
        """
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

        if self.image.ndim == 2:
            self.image = clahe.apply(self.image)
            return self

        lab = cv2.cvtColor(self.image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        l_channel = clahe.apply(l_channel)
        lab = cv2.merge((l_channel, a_channel, b_channel))
        self.image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return self

    def adjust_brightness(self, value: int) -> "ImagePreprocessor":
        """Adjust image brightness by an additive offset.

        Args:
            value: Amount to add to every pixel value. Positive values
                brighten the image; negative values darken it. Result
                is clipped to the valid ``uint8`` range.

        Returns:
            ``self``, for chaining.
        """
        self.image = cv2.convertScaleAbs(self.image, alpha=1.0, beta=value)
        return self

    def adjust_contrast(self, alpha: float) -> "ImagePreprocessor":
        """Adjust image contrast by a multiplicative gain.

        Args:
            alpha: Contrast gain. Values greater than ``1.0`` increase
                contrast; values between ``0`` and ``1.0`` decrease it.
                Result is clipped to the valid ``uint8`` range.

        Returns:
            ``self``, for chaining.
        """
        self.image = cv2.convertScaleAbs(self.image, alpha=alpha, beta=0)
        return self

    def result(self) -> np.ndarray:
        """Return the fully processed image.

        Returns:
            The image resulting from all chained operations applied so far.
        """
        return self.image
