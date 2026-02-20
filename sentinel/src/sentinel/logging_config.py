"""Logging configuration for Sentinel."""

import logging
from pathlib import Path
from typing import Optional


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """Configure logging with console and optional file output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to log file (outside vault).
    """
    # ISO-8601 timestamp format
    fmt = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    datefmt = "%Y-%m-%dT%H:%M:%SZ"

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level.upper())

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level.upper())
    console_formatter = logging.Formatter(fmt, datefmt=datefmt)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (optional, outside vault)
    if log_file:
        file_path = Path(log_file)
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(level.upper())
        file_formatter = logging.Formatter(fmt, datefmt=datefmt)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
