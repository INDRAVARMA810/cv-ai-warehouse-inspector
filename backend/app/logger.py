"""Application logging configuration.

Configures the shared Loguru logger with both console and rotating
file sinks. Importing this module has the side effect of applying the
configuration exactly once; other modules should simply::

    from app.logger import logger

    logger.info("message")
"""

import sys
from pathlib import Path

from loguru import logger

from app.config import settings

# Logs are written to ``backend/logs/app.log``, independent of the
# current working directory.
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "app.log"

_LOG_DIR.mkdir(parents=True, exist_ok=True)

# Remove the default handler so sinks are configured explicitly and
# are not duplicated if this module is imported more than once.
logger.remove()

logger.add(
    sys.stdout,
    level=settings.log_level,
    colorize=True,
    backtrace=False,
    diagnose=False,
)

logger.add(
    _LOG_FILE,
    level=settings.log_level,
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    backtrace=False,
    diagnose=False,
    enqueue=True,
)

__all__ = ["logger"]
