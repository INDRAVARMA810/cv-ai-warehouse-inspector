"""Thread-safe hand-off between the detection pipeline and MJPEG viewers.

The pipeline produces frames on a worker thread at whatever rate the
camera and GPU allow. Viewers consume them over HTTP at whatever rate
their connection allows. Those two rates are unrelated, so the manager
implements a **latest-frame-wins** hand-off:

* :meth:`StreamManager.publish` never blocks and never queues. A slow
  viewer can only ever miss intermediate frames — it can never apply
  back-pressure to the inference loop, which for a safety system must
  keep running at full rate regardless of who is watching.
* Frames are encoded **once per sequence number**, not once per viewer,
  so a second viewer costs bandwidth but almost no CPU.
* Encoding happens off the producer's critical section, so a viewer
  never delays a publish.
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

import numpy as np

from app.logger import logger
from app.streaming.frame_encoder import EncoderConfig, FrameEncoder

#: A frame older than this is treated as stale and the stream reports
#: itself as not live. Two seconds is long enough to ride out a GPU
#: hiccup, short enough that an operator is not shown a frozen image.
DEFAULT_STALE_AFTER_SECONDS = 2.0


@dataclass
class StreamStats:
    """Point-in-time view of stream throughput and demand.

    Attributes:
        live: Whether a recent frame is available.
        publishing: Whether a producer is currently attached.
        viewers: Number of connected MJPEG clients.
        frames_published: Frames handed to the manager since it started.
        frames_encoded: Frames actually encoded to JPEG. Lower than
            ``frames_published`` when nobody is watching, and far lower
            than ``viewers × frames_published`` because of caching.
        publish_fps: Recent publish rate, in frames per second.
        last_frame_age: Seconds since the most recent frame, or ``None``.
        frame_width: Width of the most recent frame, in pixels.
        frame_height: Height of the most recent frame, in pixels.
        jpeg_quality: Quality the encoder is currently using.
    """

    live: bool = False
    publishing: bool = False
    viewers: int = 0
    frames_published: int = 0
    frames_encoded: int = 0
    publish_fps: float = 0.0
    last_frame_age: Optional[float] = None
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    jpeg_quality: int = 0


class StreamManager:
    """Holds the latest annotated frame and serves it to many viewers.

    Attributes:
        encoder: The JPEG encoder used for all viewers.
        stale_after: Seconds after which the stream reports not-live.
    """

    def __init__(
        self,
        encoder: Optional[FrameEncoder] = None,
        stale_after: float = DEFAULT_STALE_AFTER_SECONDS,
    ) -> None:
        """Configure the manager.

        Args:
            encoder: JPEG encoder to use. Defaults to a new encoder with
                default settings.
            stale_after: Seconds after which a frame is considered stale.

        Raises:
            ValueError: If ``stale_after`` is not positive.
        """
        if stale_after <= 0:
            raise ValueError(f"stale_after must be positive, got {stale_after}")

        self.encoder = encoder or FrameEncoder(EncoderConfig())
        self.stale_after = stale_after

        # Guards the frame slot and all counters. Held only for pointer
        # swaps and arithmetic — never across an encode or an I/O call.
        self._lock = threading.Lock()
        # Serialises encoding so concurrent viewers do not each encode
        # the same frame. Deliberately separate from `_lock`: the
        # producer must never contend on it.
        self._encode_lock = threading.Lock()
        # Signals viewers that a new frame has landed.
        self._frame_ready = threading.Condition(self._lock)

        self._frame: Optional[np.ndarray] = None
        self._sequence: int = 0
        self._last_publish_at: Optional[float] = None

        self._encoded: Optional[bytes] = None
        self._encoded_sequence: int = -1

        self._viewers: int = 0
        self._publishers: int = 0
        self._frames_published: int = 0
        self._frames_encoded: int = 0
        self._publish_fps: float = 0.0
        self._fps_window_start: float = time.perf_counter()
        self._fps_window_frames: int = 0

    # ---------------------------------------------------------------
    # Producer side
    # ---------------------------------------------------------------

    def publish(self, frame: np.ndarray) -> int:
        """Publish a new annotated frame.

        Non-blocking. Replaces any previous frame that viewers have not
        yet consumed.

        Args:
            frame: The annotated BGR frame to publish.

        Returns:
            The sequence number assigned to the frame, or ``0`` if the
            frame was rejected as unusable.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            logger.warning("StreamManager.publish() received an empty frame; ignoring.")
            return 0

        now = time.perf_counter()

        with self._lock:
            self._frame = frame
            self._sequence += 1
            self._last_publish_at = now
            self._frames_published += 1

            # Rolling publish-rate estimate over a one-second window.
            self._fps_window_frames += 1
            elapsed = now - self._fps_window_start
            if elapsed >= 1.0:
                self._publish_fps = self._fps_window_frames / elapsed
                self._fps_window_frames = 0
                self._fps_window_start = now

            sequence = self._sequence
            self._frame_ready.notify_all()

        return sequence

    @contextmanager
    def publishing(self) -> Iterator["StreamManager"]:
        """Mark a producer as attached for the duration of a block.

        Lets :meth:`stats` distinguish "no producer running" from
        "producer running but stalled", which are very different
        conditions for an operator.

        Yields:
            This manager.
        """
        with self._lock:
            self._publishers += 1

        try:
            yield self
        finally:
            with self._lock:
                self._publishers = max(0, self._publishers - 1)
            self.clear()

    def clear(self) -> None:
        """Drop the current frame and wake any waiting viewers."""
        with self._lock:
            self._frame = None
            self._encoded = None
            self._encoded_sequence = -1
            self._last_publish_at = None
            self._frame_ready.notify_all()

        logger.debug("Stream frame buffer cleared.")

    # ---------------------------------------------------------------
    # Consumer side
    # ---------------------------------------------------------------

    def get_encoded_since(self, after_sequence: int) -> Optional[Tuple[bytes, int]]:
        """Return the latest frame as JPEG, if newer than a sequence.

        Args:
            after_sequence: The last sequence number this caller sent.
                Pass ``0`` to accept any available frame.

        Returns:
            A ``(jpeg_bytes, sequence)`` tuple, or ``None`` when no
            newer frame is available or the frame could not be encoded.
        """
        with self._lock:
            sequence = self._sequence

            if self._frame is None or sequence <= after_sequence:
                return None

            if self._encoded_sequence == sequence and self._encoded is not None:
                return self._encoded, sequence

            frame = self._frame

        # Encode outside `_lock` so the producer is never delayed by it.
        with self._encode_lock:
            with self._lock:
                # Another viewer may have encoded this frame while we
                # waited for the encode lock.
                if self._encoded_sequence == sequence and self._encoded is not None:
                    return self._encoded, sequence

            encoded = self.encoder.encode_safe(frame)

            if encoded is None:
                return None

            with self._lock:
                self._frames_encoded += 1
                # Only cache if a newer frame has not superseded this one.
                if self._sequence == sequence:
                    self._encoded = encoded
                    self._encoded_sequence = sequence

        return encoded, sequence

    def wait_for_frame(self, after_sequence: int, timeout: float = 1.0) -> bool:
        """Block until a frame newer than ``after_sequence`` arrives.

        Provided for synchronous consumers. The MJPEG generator is
        asynchronous and polls instead, so as not to hold a thread per
        viewer.

        Args:
            after_sequence: The last sequence number seen.
            timeout: Maximum seconds to wait.

        Returns:
            ``True`` if a newer frame is available, ``False`` on timeout.
        """
        deadline = time.monotonic() + timeout

        with self._frame_ready:
            while self._sequence <= after_sequence:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._frame_ready.wait(remaining)

            return True

    @contextmanager
    def viewer(self) -> Iterator["StreamManager"]:
        """Count a connected viewer for the duration of a block.

        Yields:
            This manager.
        """
        with self._lock:
            self._viewers += 1
            count = self._viewers

        logger.info(f"Stream viewer connected ({count} active).")

        try:
            yield self
        finally:
            with self._lock:
                self._viewers = max(0, self._viewers - 1)
                remaining = self._viewers

            logger.info(f"Stream viewer disconnected ({remaining} active).")

    # ---------------------------------------------------------------
    # Introspection
    # ---------------------------------------------------------------

    @property
    def viewer_count(self) -> int:
        """Number of currently connected viewers."""
        with self._lock:
            return self._viewers

    @property
    def has_frame(self) -> bool:
        """Whether any frame is currently held."""
        with self._lock:
            return self._frame is not None

    def is_live(self) -> bool:
        """Whether a recent, non-stale frame is available.

        Returns:
            ``True`` if a frame arrived within :attr:`stale_after`.
        """
        with self._lock:
            if self._frame is None or self._last_publish_at is None:
                return False
            return (time.perf_counter() - self._last_publish_at) < self.stale_after

    def stats(self) -> StreamStats:
        """Return a snapshot of stream state.

        Returns:
            The current :class:`StreamStats`.
        """
        with self._lock:
            age = (
                time.perf_counter() - self._last_publish_at
                if self._last_publish_at is not None
                else None
            )
            shape = self._frame.shape[:2] if self._frame is not None else None

            return StreamStats(
                live=self._frame is not None
                and age is not None
                and age < self.stale_after,
                publishing=self._publishers > 0,
                viewers=self._viewers,
                frames_published=self._frames_published,
                frames_encoded=self._frames_encoded,
                publish_fps=round(self._publish_fps, 1),
                last_frame_age=round(age, 3) if age is not None else None,
                frame_height=shape[0] if shape else None,
                frame_width=shape[1] if shape else None,
                jpeg_quality=self.encoder.quality,
            )


#: Process-wide manager. MJPEG viewers and the pipeline worker must
#: share one instance, so the frame handed to a viewer is the frame the
#: pipeline just produced.
_manager: Optional[StreamManager] = None
_manager_lock = threading.Lock()


def get_stream_manager() -> StreamManager:
    """Return the process-wide :class:`StreamManager`.

    Returns:
        The shared manager, created on first call.
    """
    global _manager

    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = StreamManager()

    return _manager


def set_stream_manager(manager: Optional[StreamManager]) -> None:
    """Replace the process-wide manager.

    Intended for tests.

    Args:
        manager: The manager to install, or ``None`` to clear it.
    """
    global _manager

    with _manager_lock:
        _manager = manager
