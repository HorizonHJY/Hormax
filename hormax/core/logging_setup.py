"""Logging setup for the Hormax package.

This module provides centralized logging configuration following
the project's logging principles.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from hormax.core.config import LoggingConfig


def setup_logging(config: Optional[LoggingConfig] = None) -> logging.Logger:
    """Set up logging for the Hormax package.

    Args:
        config: Logging configuration. If None, uses default configuration.

    Returns:
        Configured root logger for the Hormax package.
    """
    if config is None:
        config = LoggingConfig()

    # Get or create the hormax logger
    logger = logging.getLogger("hormax")
    logger.setLevel(getattr(logging, config.level))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(config.format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if configured)
    if config.file:
        log_file = Path(config.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, config.level))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (e.g., 'hormax.finance.stocks').

    Returns:
        Logger instance for the module.
    """
    return logging.getLogger(name)
