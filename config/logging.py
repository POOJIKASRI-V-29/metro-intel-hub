"""Centralized logging utility configuration for the KMRL platform.

Scope: Sets up the system-wide console logging format, handles log thresholds, 
and provides a safe wrapper to prevent log duplication across the AI pipelines.
"""

from __future__ import annotations

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Configures and retrieves a standardized logger instance.

    Args:
        name: The name of the calling module (typically pass __name__).

    Returns:
        A configured logging.Logger instance.
    """
    # Explicitly fetch from the global manager to avoid local file namespace confusion
    logger = logging.Logger.manager.getLogger(name)

    # Set visibility window threshold (DEBUG shows prompts, INFO hides them)
    logger.setLevel(logging.DEBUG)

    # Avoid adding multiple duplicate handlers when files are imported recursively
    if not logger.handlers:
        # Standard format: timestamp [module path] LOG_LEVEL - log message
        formatter = logging.Formatter(
            fmt="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Route all outputs cleanly to standard output for terminal printing
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Block message bubble-up to prevent duplicate printing by the root logger
        logger.propagate = False

    return logger