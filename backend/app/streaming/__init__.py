"""Live MJPEG video streaming.

Publishes the annotated frames produced by the detection pipeline as a
``multipart/x-mixed-replace`` stream that any browser can render in a
plain ``<img>`` tag.

The layer separates four concerns:

* :mod:`app.streaming.frame_encoder` turns BGR frames into JPEG bytes.
* :mod:`app.streaming.stream_manager` holds the latest frame and hands
  it to many viewers without ever blocking the pipeline.
* :mod:`app.streaming.stream` drives the existing detection pipeline on
  a worker thread and publishes what it renders.
* :mod:`app.streaming.mjpeg` formats those frames as a multipart HTTP
  response.

Importing this package is cheap: OpenCV, Torch and Ultralytics are
imported only when a stream actually starts.
"""

from app.streaming.frame_encoder import EncoderConfig, EncodingError, FrameEncoder
from app.streaming.mjpeg import (
    BOUNDARY,
    MJPEG_CONTENT_TYPE,
    STREAM_HEADERS,
    build_frame_part,
    mjpeg_stream,
    snapshot,
)
from app.streaming.stream import (
    StreamConfig,
    StreamError,
    VideoStream,
    get_video_stream,
    set_video_stream,
    shutdown_stream,
)
from app.streaming.stream_manager import (
    StreamManager,
    StreamStats,
    get_stream_manager,
    set_stream_manager,
)

__all__ = [
    "FrameEncoder",
    "EncoderConfig",
    "EncodingError",
    "StreamManager",
    "StreamStats",
    "get_stream_manager",
    "set_stream_manager",
    "VideoStream",
    "StreamConfig",
    "StreamError",
    "get_video_stream",
    "set_video_stream",
    "shutdown_stream",
    "mjpeg_stream",
    "snapshot",
    "build_frame_part",
    "BOUNDARY",
    "MJPEG_CONTENT_TYPE",
    "STREAM_HEADERS",
]
