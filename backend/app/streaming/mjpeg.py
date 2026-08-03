"""MJPEG (``multipart/x-mixed-replace``) response generation.

Motion JPEG is a sequence of complete JPEG images pushed down one
never-ending HTTP response, each preceded by a boundary and its own
headers. Every browser can render it in a plain ``<img>`` tag with no
client-side code, which is why it remains the pragmatic choice for a
monitoring dashboard even though it is far less efficient than a real
video codec.

The generator here is **asynchronous and polls**. Blocking on a
condition variable would be more elegant, but a synchronous generator
under Starlette occupies a threadpool thread for the entire life of the
connection — with a handful of viewers that exhausts the pool and
stalls the whole API. Polling at the frame interval costs a wakeup per
viewer per frame and keeps the event loop free.
"""

import asyncio
import time
from typing import AsyncIterator, Optional

from app.logger import logger
from app.streaming.stream_manager import StreamManager

#: Multipart boundary token. Arbitrary, but must not appear in payload.
BOUNDARY = "frameboundary"

#: Content type clients receive, including the boundary declaration.
MJPEG_CONTENT_TYPE = f"multipart/x-mixed-replace; boundary={BOUNDARY}"

#: Headers that stop proxies and browsers from buffering or caching a
#: stream that is, by definition, never complete and never reusable.
STREAM_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate, private",
    "Pragma": "no-cache",
    "Expires": "0",
    # Defeats nginx response buffering, which otherwise holds frames
    # back until its buffer fills and makes the stream look frozen.
    "X-Accel-Buffering": "no",
    "Connection": "close",
}

#: Upper bound on how long a viewer waits with no new frame before the
#: connection is closed, so a dead producer does not leave sockets open.
DEFAULT_IDLE_TIMEOUT_SECONDS = 30.0


def build_frame_part(jpeg: bytes) -> bytes:
    """Wrap encoded JPEG bytes in a multipart part.

    Args:
        jpeg: The encoded JPEG image.

    Returns:
        The boundary, part headers and payload as a single byte string.
    """
    return b"".join(
        (
            b"--",
            BOUNDARY.encode("ascii"),
            b"\r\n",
            b"Content-Type: image/jpeg\r\n",
            b"Content-Length: ",
            str(len(jpeg)).encode("ascii"),
            b"\r\n\r\n",
            jpeg,
            b"\r\n",
        )
    )


async def mjpeg_stream(
    manager: StreamManager,
    target_fps: float = 20.0,
    idle_timeout: float = DEFAULT_IDLE_TIMEOUT_SECONDS,
) -> AsyncIterator[bytes]:
    """Yield an MJPEG byte stream for one viewer.

    Sends only frames the pipeline has actually produced: if inference
    runs slower than ``target_fps`` the stream simply slows down, and if
    it runs faster the extra frames are skipped rather than queued.

    Args:
        manager: The manager holding the latest frame.
        target_fps: Maximum frames per second sent to this viewer.
        idle_timeout: Seconds without a new frame before the stream is
            closed.

    Yields:
        Multipart chunks, each containing one JPEG frame.

    Raises:
        ValueError: If ``target_fps`` is not positive.
    """
    if target_fps <= 0:
        raise ValueError(f"target_fps must be positive, got {target_fps}")

    frame_interval = 1.0 / target_fps
    # Poll noticeably faster than the frame rate so a new frame is
    # picked up promptly rather than sitting for a whole interval.
    poll_interval = min(frame_interval / 2.0, 0.02)

    last_sequence = 0
    last_sent_at = 0.0
    idle_since = time.monotonic()

    with manager.viewer():
        try:
            while True:
                now = time.monotonic()

                # Respect the viewer's frame budget.
                if now - last_sent_at < frame_interval:
                    await asyncio.sleep(poll_interval)
                    continue

                result = manager.get_encoded_since(last_sequence)

                if result is None:
                    if now - idle_since > idle_timeout:
                        logger.info(
                            f"Closing MJPEG stream: no frame for {idle_timeout:.0f}s."
                        )
                        return
                    await asyncio.sleep(poll_interval)
                    continue

                jpeg, sequence = result
                last_sequence = sequence
                last_sent_at = now
                idle_since = now

                yield build_frame_part(jpeg)

        except asyncio.CancelledError:
            # Raised when the client disconnects. Expected, not an error.
            logger.debug("MJPEG stream cancelled by client disconnect.")
            raise
        except GeneratorExit:
            logger.debug("MJPEG generator closed.")
            raise
        except Exception:
            logger.exception("Unexpected error in MJPEG stream; closing connection.")
            return


async def snapshot(manager: StreamManager, timeout: float = 2.0) -> Optional[bytes]:
    """Return a single current JPEG frame.

    Useful for thumbnails and for probing whether the stream is
    producing anything, without opening a long-lived connection.

    Args:
        manager: The manager holding the latest frame.
        timeout: Seconds to wait for a frame to become available.

    Returns:
        The encoded JPEG, or ``None`` if no frame arrived in time.
    """
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        result = manager.get_encoded_since(0)
        if result is not None:
            return result[0]
        await asyncio.sleep(0.05)

    return None
