"""Real-time frame-rate measurement and on-frame display.

Provides :class:`FPSCounter`, which measures frames-per-second over a
rolling time window and can overlay the current value onto a frame.
"""

import time
from typing import Tuple

import cv2
import numpy as np


class FPSCounter:
    """Measures and displays real-time frames-per-second (FPS).

    FPS is computed over a rolling window of ``reset_interval`` seconds;
    the internal frame counter and timer reset automatically at the end
    of each window, so the reported value reflects recent throughput
    rather than a cumulative average since startup.

    Attributes:
        reset_interval: Seconds between automatic FPS recalculations.
    """

    def __init__(self, reset_interval: float = 1.0) -> None:
        """Initialize the counter.

        Args:
            reset_interval: How often, in seconds, the FPS value is
                recalculated and the internal counters reset.
        """
        self.reset_interval = reset_interval
        self._frame_count: int = 0
        self._window_start: float = time.perf_counter()
        self._fps: float = 0.0

    def update(self) -> float:
        """Register that one frame has been processed.

        Call this once per loop iteration. The FPS estimate is
        recalculated, and the internal counters reset, once
        ``reset_interval`` seconds have elapsed since the last
        recalculation.

        Returns:
            The current FPS estimate.
        """
        self._frame_count += 1
        elapsed = time.perf_counter() - self._window_start

        if elapsed >= self.reset_interval:
            self._fps = self._frame_count / elapsed
            self._frame_count = 0
            self._window_start = time.perf_counter()

        return self._fps

    def reset(self) -> None:
        """Manually reset the counter's window and accumulated state."""
        self._frame_count = 0
        self._window_start = time.perf_counter()
        self._fps = 0.0

    def get_fps(self) -> float:
        """Return the most recently calculated FPS value."""
        return self._fps

    def overlay(
        self,
        frame: np.ndarray,
        position: Tuple[int, int] = (10, 30),
        color: Tuple[int, int, int] = (0, 255, 0),
        font_scale: float = 0.8,
        thickness: int = 2,
    ) -> np.ndarray:
        """Draw the current FPS value onto a frame, in place.

        Args:
            frame: The frame to annotate (modified in place).
            position: Bottom-left corner of the text, in pixels.
            color: BGR text color.
            font_scale: OpenCV font scale factor.
            thickness: Text stroke thickness, in pixels.

        Returns:
            The annotated frame (the same object passed in as ``frame``).
        """
        cv2.putText(
            frame,
            f"FPS: {self._fps:.1f}",
            position,
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA,
        )
        return frame
