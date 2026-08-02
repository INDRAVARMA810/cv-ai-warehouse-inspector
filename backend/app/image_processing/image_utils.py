"""Reusable, stateless helper functions for image manipulation.

These utilities are intentionally independent of :class:`ImagePreprocessor`
so they can be used freely by preprocessing, augmentation, and future
inference code without introducing coupling.
"""

from pathlib import Path
from typing import Tuple, Union

import cv2
import numpy as np

from app.logger import logger


def load_image(path: Union[str, Path]) -> np.ndarray:
    """Load an image from disk into a BGR ``numpy.ndarray``.

    Args:
        path: Filesystem path to the image file.

    Returns:
        The decoded image in BGR order, as produced by OpenCV.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If the file exists but could not be decoded as an image.
    """
    image_path = Path(path)

    if not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Unable to decode image file: {image_path}")

    return image


def save_image(path: Union[str, Path], image: np.ndarray) -> bool:
    """Write an image to disk, creating parent directories if needed.

    Args:
        path: Destination filesystem path, including file extension.
        image: The image to write.

    Returns:
        ``True`` if the image was written successfully, ``False`` otherwise.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    success = cv2.imwrite(str(output_path), image)

    if not success:
        logger.warning(f"Failed to write image to: {output_path}")

    return bool(success)


def get_dimensions(image: np.ndarray) -> Tuple[int, int]:
    """Return an image's spatial dimensions.

    Args:
        image: Input image, grayscale or color.

    Returns:
        A ``(height, width)`` tuple, in pixels.
    """
    height, width = image.shape[:2]
    return height, width


def is_grayscale(image: np.ndarray) -> bool:
    """Return whether an image has a single channel (grayscale).

    Args:
        image: Input image.

    Returns:
        ``True`` if the image is 2-D or has exactly one channel.
    """
    return image.ndim == 2 or (image.ndim == 3 and image.shape[2] == 1)


def ensure_channels(image: np.ndarray, channels: int = 3) -> np.ndarray:
    """Ensure an image has the requested number of channels.

    Converts between grayscale and BGR as needed. No-op if the image
    already has the requested channel count.

    Args:
        image: Input image.
        channels: Desired channel count; must be ``1`` or ``3``.

    Returns:
        An image with exactly ``channels`` channels.

    Raises:
        ValueError: If ``channels`` is not ``1`` or ``3``.
    """
    if channels not in (1, 3):
        raise ValueError(f"Unsupported channel count: {channels} (expected 1 or 3)")

    currently_gray = is_grayscale(image)

    if channels == 1 and not currently_gray:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if channels == 3 and currently_gray:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    return image


def to_uint8(image: np.ndarray) -> np.ndarray:
    """Convert a (possibly float, possibly out-of-range) image to ``uint8``.

    Useful for preparing a normalized or otherwise float-valued image
    for display or disk I/O, both of which expect 8-bit pixel values.

    Args:
        image: Input image of any numeric dtype.

    Returns:
        The image clipped to ``[0, 255]`` and cast to ``uint8``.
    """
    if image.dtype == np.uint8:
        return image

    return np.clip(image, 0, 255).astype(np.uint8)


def crop(image: np.ndarray, x: int, y: int, width: int, height: int) -> np.ndarray:
    """Crop a rectangular region from an image.

    Args:
        image: Input image.
        x: Left edge of the crop region, in pixels.
        y: Top edge of the crop region, in pixels.
        width: Width of the crop region, in pixels.
        height: Height of the crop region, in pixels.

    Returns:
        The cropped region as a view into ``image``.

    Raises:
        ValueError: If the requested region falls outside the image bounds.
    """
    image_height, image_width = get_dimensions(image)

    if x < 0 or y < 0 or x + width > image_width or y + height > image_height:
        raise ValueError(
            f"Crop region ({x}, {y}, {width}, {height}) is out of bounds "
            f"for image of size ({image_width}, {image_height})"
        )

    return image[y : y + height, x : x + width]


def pad(
    image: np.ndarray,
    top: int,
    bottom: int,
    left: int,
    right: int,
    color: Tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    """Pad an image with a solid border.

    Args:
        image: Input image.
        top: Border size to add above the image, in pixels.
        bottom: Border size to add below the image, in pixels.
        left: Border size to add to the left of the image, in pixels.
        right: Border size to add to the right of the image, in pixels.
        color: BGR fill color for the border.

    Returns:
        The padded image.
    """
    return cv2.copyMakeBorder(
        image, top, bottom, left, right, borderType=cv2.BORDER_CONSTANT, value=color
    )
