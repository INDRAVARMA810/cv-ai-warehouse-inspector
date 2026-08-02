"""Training-time image augmentation functions.

Each function is a pure, stateless transform that takes an image and
returns a new augmented image. They are designed to be called
independently (e.g. with randomized parameters) from a training data
pipeline, rather than chained like :class:`ImagePreprocessor`.
"""

import cv2
import numpy as np


def horizontal_flip(image: np.ndarray) -> np.ndarray:
    """Flip an image horizontally (left-right, mirror across the y-axis).

    Args:
        image: Input image.

    Returns:
        The horizontally flipped image.
    """
    return cv2.flip(image, 1)


def vertical_flip(image: np.ndarray) -> np.ndarray:
    """Flip an image vertically (top-bottom, mirror across the x-axis).

    Args:
        image: Input image.

    Returns:
        The vertically flipped image.
    """
    return cv2.flip(image, 0)


def rotate(image: np.ndarray, angle: float, scale: float = 1.0) -> np.ndarray:
    """Rotate an image about its center.

    Args:
        image: Input image.
        angle: Rotation angle in degrees. Positive values rotate
            counter-clockwise.
        scale: Isotropic scale factor applied during rotation.

    Returns:
        The rotated image, with the same dimensions as the input
        (corners introduced by rotation are filled with black).
    """
    height, width = image.shape[:2]
    center = (width / 2.0, height / 2.0)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)
    return cv2.warpAffine(image, rotation_matrix, (width, height))


def scale(
    image: np.ndarray,
    factor: float,
    interpolation: int = cv2.INTER_LINEAR,
) -> np.ndarray:
    """Scale an image's spatial dimensions by a factor.

    Args:
        image: Input image.
        factor: Scale factor; values greater than ``1.0`` enlarge the
            image, values between ``0`` and ``1.0`` shrink it.
        interpolation: OpenCV interpolation flag.

    Returns:
        The scaled image.

    Raises:
        ValueError: If ``factor`` is not positive.
    """
    if factor <= 0:
        raise ValueError(f"factor must be positive, got {factor}")

    height, width = image.shape[:2]
    new_width = max(1, round(width * factor))
    new_height = max(1, round(height * factor))
    return cv2.resize(image, (new_width, new_height), interpolation=interpolation)


def adjust_brightness(image: np.ndarray, value: int) -> np.ndarray:
    """Adjust image brightness by an additive offset.

    Args:
        image: Input image.
        value: Amount to add to every pixel value. Positive values
            brighten the image; negative values darken it. Result is
            clipped to the valid ``uint8`` range.

    Returns:
        The brightness-adjusted image.
    """
    return cv2.convertScaleAbs(image, alpha=1.0, beta=value)


def gaussian_noise(image: np.ndarray, mean: float = 0.0, sigma: float = 25.0) -> np.ndarray:
    """Add Gaussian (normally distributed) noise to an image.

    Args:
        image: Input image.
        mean: Mean of the Gaussian noise distribution.
        sigma: Standard deviation of the Gaussian noise distribution;
            higher values produce noisier output.

    Returns:
        The noisy image, clipped to the valid ``uint8`` range.
    """
    noise = np.random.normal(mean, sigma, image.shape).astype(np.float32)
    noisy_image = image.astype(np.float32) + noise
    return np.clip(noisy_image, 0, 255).astype(np.uint8)
