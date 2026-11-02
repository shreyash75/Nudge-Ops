import sys

from loguru import logger


def setup_logging() -> None:
    """Configure Loguru for structured, readable logs."""

    logger.remove()
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        level="INFO",
        backtrace=False,
        diagnose=False,
    )
