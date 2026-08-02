"""Manual demo script for the video input pipeline.

Opens the default webcam, displays the live feed with a real-time FPS
overlay, and exits cleanly when the user presses "q".

Run from the ``backend/`` directory with:

    python run_camera.py
"""

import cv2

from app.logger import logger
from app.video.camera import Camera, CameraError
from app.video.fps import FPSCounter
from app.video.video_reader import VideoReader

WINDOW_NAME = "AI Warehouse Safety Inspector - Camera Feed"
QUIT_KEY = "q"


def main() -> None:
    """Run the live webcam preview loop with an FPS overlay."""
    camera = Camera(source=0)
    reader = VideoReader()
    fps_counter = FPSCounter()

    try:
        camera.open()
    except CameraError as exc:
        logger.error(f"Failed to start camera: {exc}")
        return

    logger.info(f"Camera feed started. Press '{QUIT_KEY.upper()}' to quit.")

    try:
        while True:
            frame = camera.read()
            if frame is None:
                logger.warning("No frame received from camera; stopping.")
                break

            processed = reader.process(frame)
            fps_counter.update()
            fps_counter.overlay(processed)

            cv2.imshow(WINDOW_NAME, processed)

            if cv2.waitKey(1) & 0xFF == ord(QUIT_KEY):
                logger.info("Quit key pressed; stopping camera feed.")
                break
    except Exception:
        logger.exception("Unexpected error in camera feed loop.")
    finally:
        camera.release()
        cv2.destroyAllWindows()
        logger.info("Camera resources released and windows closed.")


if __name__ == "__main__":
    main()
