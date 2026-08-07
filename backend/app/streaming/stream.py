"""Video stream source: runs the detection pipeline and publishes frames.

Bridges the existing offline pipeline to the live stream. A
:class:`VideoStream` owns a worker thread that reads from the camera,
runs the **existing** ``SafetyPipeline`` — the same detect → track →
evaluate chain used by ``run_detection.py``, not a reimplementation of
it — and publishes each annotated frame to the shared
:class:`~app.streaming.stream_manager.StreamManager`.

Running in-process matters: the manager is a process-wide singleton, so
frames produced by a separate ``run_detection.py`` process are **not**
visible to the API. The stream must be driven from inside the API
process for viewers to see anything.

Heavy dependencies (OpenCV, Torch, Ultralytics) are imported lazily
inside :meth:`VideoStream.start`, so importing :mod:`app.streaming` — and
therefore the whole API — stays cheap and works on machines with no
camera or GPU.
"""

import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional, Union

from app.logger import logger
from app.streaming.stream_manager import StreamManager, get_stream_manager


class StreamError(Exception):
    """Raised when the video stream cannot be started or run."""


def _env_str(name: str, default: str) -> str:
    """Read a string from the environment."""
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    """Read a float from the environment, falling back on bad input."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning(f"{name}={raw!r} is not a number; using default {default}.")
        return default


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean from the environment."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class StreamConfig:
    """Configuration for a :class:`VideoStream`.

    Attributes:
        source: Webcam index or path to a video file.
        weights: YOLO weights path or built-in model name.
        device: Compute device, or ``None`` to select automatically.
        confidence_threshold: Minimum detection confidence.
        iou_threshold: NMS IoU threshold.
        resize_width: Width to resize frames to before inference.
            Streaming and inference both benefit from a smaller frame.
        resize_height: Height to resize frames to before inference.
        frame_rate: Expected source frame rate, used to size the
            tracker's lost-track buffer.
        loop_video: Restart a video file when it ends. Useful for demo
            footage; meaningless for a live camera.
        auto_start: Whether the stream starts on the first viewer.
        idle_stop_seconds: Stop the camera after this long with no
            viewers. ``0`` keeps it running indefinitely. Releasing an
            idle camera frees the device and stops burning GPU time on
            frames nobody is watching.
    """

    source: Union[int, str] = 0
    weights: str = "yolov8n.pt"
    device: Optional[str] = None
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    resize_width: int = 960
    resize_height: int = 540
    frame_rate: int = 30
    loop_video: bool = True
    auto_start: bool = True
    idle_stop_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "StreamConfig":
        """Build configuration from environment variables.

        Reads ``STREAM_SOURCE``, ``STREAM_WEIGHTS``, ``STREAM_DEVICE``,
        ``STREAM_CONF``, ``STREAM_IOU``, ``STREAM_WIDTH``,
        ``STREAM_HEIGHT``, ``STREAM_FPS``, ``STREAM_LOOP``,
        ``STREAM_AUTO_START`` and ``STREAM_IDLE_STOP``.

        Returns:
            The resulting configuration.
        """
        raw_source = _env_str("STREAM_SOURCE", "0")
        try:
            source: Union[int, str] = int(raw_source)
        except ValueError:
            source = raw_source

        return cls(
            source=source,
            weights=_env_str("STREAM_WEIGHTS", "yolov8n.pt"),
            device=os.getenv("STREAM_DEVICE") or None,
            confidence_threshold=_env_float("STREAM_CONF", 0.25),
            iou_threshold=_env_float("STREAM_IOU", 0.45),
            resize_width=int(_env_float("STREAM_WIDTH", 960)),
            resize_height=int(_env_float("STREAM_HEIGHT", 540)),
            frame_rate=int(_env_float("STREAM_FPS", 30)),
            loop_video=_env_bool("STREAM_LOOP", True),
            auto_start=_env_bool("STREAM_AUTO_START", True),
            idle_stop_seconds=_env_float("STREAM_IDLE_STOP", 60.0),
        )


class VideoStream:
    """Runs the detection pipeline on a worker thread and publishes frames.

    Attributes:
        config: The stream configuration in effect.
        manager: The manager frames are published to.
    """

    def __init__(
        self,
        config: Optional[StreamConfig] = None,
        manager: Optional[StreamManager] = None,
    ) -> None:
        """Configure the stream without opening the camera.

        Args:
            config: Stream configuration. Defaults to
                :meth:`StreamConfig.from_env`.
            manager: Manager to publish to. Defaults to the shared one.
        """
        self.config = config or StreamConfig.from_env()
        self.manager = manager or get_stream_manager()

        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._last_error: Optional[str] = None
        self._started_at: Optional[float] = None
        self._device: Optional[str] = None

    # ---------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Whether the worker thread is alive."""
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def last_error(self) -> Optional[str]:
        """The most recent startup or runtime failure, if any."""
        return self._last_error

    @property
    def device(self) -> Optional[str]:
        """Compute device the pipeline resolved to, once started."""
        return self._device

    @property
    def uptime(self) -> Optional[float]:
        """Seconds since the stream started, or ``None`` if stopped."""
        return time.time() - self._started_at if self._started_at else None

    def start(self) -> bool:
        """Start the capture and inference thread.

        Idempotent: calling it while already running is a no-op.

        Returns:
            ``True`` if the stream is running when this returns.
        """
        with self._lock:
            if self.is_running:
                return True

            self._stop.clear()
            self._last_error = None

            thread = threading.Thread(
                target=self._run,
                name="video-stream",
                daemon=True,
            )
            self._thread = thread
            thread.start()

        # Give the worker a moment to fail loudly (bad camera, missing
        # weights) so the caller can report the reason rather than
        # returning success for a stream that died immediately.
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if self._last_error is not None:
                logger.error(f"Video stream failed to start: {self._last_error}")
                return False
            if self.manager.has_frame:
                return True
            if not self.is_running:
                return False
            time.sleep(0.1)

        # Still starting (model download, slow camera). Report running.
        return self.is_running

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the worker to stop and wait for it to exit.

        Args:
            timeout: Seconds to wait for the thread to finish.
        """
        self._stop.set()

        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)

            if thread.is_alive():
                logger.warning("Video stream thread did not exit within timeout.")

        self._thread = None
        self._started_at = None
        logger.info("Video stream stopped.")

    def ensure_started(self) -> bool:
        """Start the stream if auto-start is enabled and it is not running.

        Returns:
            ``True`` if the stream is running.
        """
        if self.is_running:
            return True

        if not self.config.auto_start:
            return False

        logger.info("Auto-starting video stream for an incoming viewer.")
        return self.start()

    # ---------------------------------------------------------------
    # Worker
    # ---------------------------------------------------------------

    def _build_pipeline(self) -> Any:
        """Construct the existing detection pipeline.

        Imported lazily so the API can be imported without OpenCV,
        Torch or a GPU present.

        Returns:
            A configured ``SafetyPipeline``.

        Raises:
            StreamError: If the pipeline cannot be constructed.
        """
        try:
            # `run_detection` lives at the backend root and is importable
            # when the API is launched from that directory, which is how
            # every documented run command starts it.
            from run_detection import PipelineConfig, SafetyPipeline
        except ImportError as exc:
            raise StreamError(
                "Cannot import the detection pipeline (run_detection). "
                "Start the API from the backend/ directory so it is on "
                f"the import path. Original error: {exc}"
            ) from exc

        try:
            pipeline_config = PipelineConfig(
                source=self.config.source,
                weights=self.config.weights,
                device=self.config.device,
                confidence_threshold=self.config.confidence_threshold,
                iou_threshold=self.config.iou_threshold,
                resize_to=(self.config.resize_width, self.config.resize_height),
                frame_rate=self.config.frame_rate,
            )
            return SafetyPipeline(pipeline_config)
        except Exception as exc:
            raise StreamError(f"Failed to build the detection pipeline: {exc}") from exc

    def _run(self) -> None:
        """Worker body: capture, infer, annotate, publish."""
        try:
            from app.video import Camera, CameraError
        except ImportError as exc:
            self._last_error = f"OpenCV is not available: {exc}"
            return

        try:
            pipeline = self._build_pipeline()
        except StreamError as exc:
            self._last_error = str(exc)
            return

        from app.streaming.persistence import LivePersistence

        persistence = LivePersistence()

        self._device = getattr(pipeline, "device", None)
        camera = Camera(source=self.config.source)

        try:
            camera.open()
        except CameraError as exc:
            self._last_error = f"Cannot open video source {self.config.source!r}: {exc}"
            logger.error(self._last_error)
            return

        self._started_at = time.time()
        logger.info(
            f"Video stream started: source={self.config.source!r}, "
            f"device={self._device}, weights={self.config.weights}"
        )

        consecutive_failures = 0
        idle_since: Optional[float] = None

        try:
            with self.manager.publishing():
                while not self._stop.is_set():
                    # Release the camera if nobody has watched for a while.
                    if self.config.idle_stop_seconds > 0:
                        if self.manager.viewer_count == 0:
                            idle_since = idle_since or time.monotonic()
                            if time.monotonic() - idle_since > self.config.idle_stop_seconds:
                                logger.info(
                                    "Stopping video stream: no viewers for "
                                    f"{self.config.idle_stop_seconds:.0f}s."
                                )
                                break
                        else:
                            idle_since = None

                    frame = camera.read()

                    if frame is None:
                        consecutive_failures += 1

                        if self._restart_video_source(camera):
                            consecutive_failures = 0
                            continue

                        if consecutive_failures >= 30:
                            self._last_error = (
                                "Video source stopped delivering frames."
                            )
                            logger.warning(self._last_error)
                            break

                        time.sleep(0.05)
                        continue

                    consecutive_failures = 0

                    try:
                        outcome = pipeline.process_frame(frame)
                        annotated = pipeline.render(outcome)
                    except Exception:
                        logger.exception("Pipeline failed on a frame; skipping it.")
                        continue

                    persistence.record(outcome.rule_result, outcome.tracked_objects)

                    pipeline.fps_counter.update()
                    self.manager.publish(annotated)

        except Exception:
            self._last_error = "Unexpected error in the video stream worker."
            logger.exception(self._last_error)
        finally:
            camera.release()
            self._started_at = None
            logger.info("Video stream worker exited; camera released.")

    def _restart_video_source(self, camera: Any) -> bool:
        """Reopen a finished video file when looping is enabled.

        A live camera returning no frame is a fault; a *file* returning
        no frame simply means it ended, which for demo footage should
        loop rather than terminate the stream.

        Args:
            camera: The camera wrapper to reopen.

        Returns:
            ``True`` if the source was reopened.
        """
        is_file = isinstance(self.config.source, str)

        if not (is_file and self.config.loop_video):
            return False

        try:
            camera.release()
            camera.open()
            logger.debug("Looped video source back to the start.")
            return True
        except Exception as exc:
            logger.warning(f"Could not loop video source: {exc}")
            return False


#: Process-wide stream, so every viewer shares one camera and one
#: inference loop rather than each opening their own.
_stream: Optional[VideoStream] = None
_stream_lock = threading.Lock()


def get_video_stream() -> VideoStream:
    """Return the process-wide :class:`VideoStream`.

    Returns:
        The shared stream, created on first call.
    """
    global _stream

    if _stream is None:
        with _stream_lock:
            if _stream is None:
                _stream = VideoStream()

    return _stream


def set_video_stream(stream: Optional[VideoStream]) -> None:
    """Replace the process-wide stream.

    Intended for tests.

    Args:
        stream: The stream to install, or ``None`` to clear it.
    """
    global _stream

    with _stream_lock:
        if _stream is not None and _stream is not stream:
            _stream.stop()
        _stream = stream


def shutdown_stream() -> None:
    """Stop the shared stream, if one is running."""
    global _stream

    with _stream_lock:
        if _stream is not None:
            _stream.stop()
