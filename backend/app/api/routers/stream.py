"""Live video streaming endpoints.

Exposes the annotated detection feed as MJPEG, plus a status endpoint
the dashboard uses to decide between showing the feed, a loading state,
or an explanation of why no video is available.
"""

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from app.api.schemas import StreamStatusResponse
from app.logger import logger
from app.streaming import (
    MJPEG_CONTENT_TYPE,
    STREAM_HEADERS,
    get_stream_manager,
    get_video_stream,
    mjpeg_stream,
    snapshot,
)

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get(
    "/live",
    summary="Live MJPEG video stream",
    description=(
        "Streams the annotated detection feed as `multipart/x-mixed-replace`. "
        "Render it directly in an `<img>` tag — no client-side decoding is "
        "needed. The connection stays open until the client disconnects or the "
        "producer stops delivering frames.\n\n"
        "Returns **503** when no video source is available, so a client can "
        "distinguish 'not started' from 'started but silent'."
    ),
    responses={
        200: {
            "content": {"multipart/x-mixed-replace": {}},
            "description": "An open MJPEG stream.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "No video source is available."
        },
    },
)
def stream_live(
    fps: float = Query(
        default=20.0,
        gt=0,
        le=60,
        description="Maximum frames per second delivered to this viewer.",
    ),
) -> StreamingResponse:
    """Open an MJPEG stream for one viewer.

    Args:
        fps: Maximum frames per second for this connection.

    Returns:
        A streaming multipart response.

    Raises:
        HTTPException: With ``503`` if no video source can be started.
    """
    stream = get_video_stream()
    manager = get_stream_manager()

    if not stream.ensure_started():
        detail = stream.last_error or (
            "No video source is running and automatic start is disabled."
        )
        logger.warning(f"Refusing MJPEG connection: {detail}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail
        )

    return StreamingResponse(
        mjpeg_stream(manager, target_fps=fps),
        media_type=MJPEG_CONTENT_TYPE,
        headers=dict(STREAM_HEADERS),
    )


@router.get(
    "/snapshot",
    summary="Single frame snapshot",
    description=(
        "Returns the most recent annotated frame as a single JPEG. Cheaper "
        "than opening a stream when only a still image is needed."
    ),
    responses={
        200: {"content": {"image/jpeg": {}}, "description": "The latest frame."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "No frame available."},
    },
)
async def stream_snapshot() -> Response:
    """Return the latest frame as a JPEG image.

    Returns:
        The encoded frame.

    Raises:
        HTTPException: With ``503`` if no frame is available.
    """
    stream = get_video_stream()
    manager = get_stream_manager()

    if not stream.ensure_started():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=stream.last_error or "No video source is running.",
        )

    image = await snapshot(manager)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No frame has been produced yet.",
        )

    return Response(
        content=image,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.get(
    "/status",
    response_model=StreamStatusResponse,
    summary="Stream status",
    description=(
        "Reports whether the pipeline is running and delivering frames, plus "
        "throughput and viewer counts. Always returns 200 so a dashboard can "
        "poll it to decide what to display."
    ),
)
def stream_status() -> StreamStatusResponse:
    """Report the current state of the video stream.

    Returns:
        The stream's status and throughput figures.
    """
    stream = get_video_stream()
    stats = get_stream_manager().stats()

    return StreamStatusResponse(
        available=stats.live,
        running=stream.is_running,
        auto_start=stream.config.auto_start,
        viewers=stats.viewers,
        frames_published=stats.frames_published,
        frames_encoded=stats.frames_encoded,
        publish_fps=stats.publish_fps,
        last_frame_age=stats.last_frame_age,
        frame_width=stats.frame_width,
        frame_height=stats.frame_height,
        jpeg_quality=stats.jpeg_quality,
        device=stream.device,
        source=str(stream.config.source),
        uptime=stream.uptime,
        error=stream.last_error,
    )
