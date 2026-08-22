"""Centralized logging configuration for the KMRL Document Intelligence Platform.

This module must be configured exactly once, at process startup (typically
from `api/main.py`'s startup event, or at the top of a standalone script /
pytest `conftest.py`). After `configure_logging()` has run, every other
module should obtain its logger via:

    from config.logging import get_logger
    logger = get_logger(__name__)

No module should call `logging.basicConfig()` or attach handlers directly.

Typical usage example:

    from config.logging import configure_logging, get_logger

    configure_logging()
    logger = get_logger(__name__)
    logger.info("Application startup complete")
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import LoggingSettings, get_settings

_CONFIGURED: bool = False
"""Module-level guard preventing duplicate handler attachment on repeated calls."""


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Intended for production environments where logs are shipped to an
    aggregator (e.g. ELK, Loki, CloudWatch) that expects structured input.

    Attributes:
        None. This formatter is stateless beyond what `logging.Formatter`
        already tracks.
    """

    _RESERVED_ATTRS = frozenset(
        {
            "name", "msg", "args", "levelname", "levelno", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process", "message",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        """Renders a single log record as a JSON string.

        Args:
            record: The log record emitted by a logger.

        Returns:
            A single-line JSON string representing the record, including
            any `extra=` fields passed by the caller, and a formatted
            exception traceback if present.
        """
        payload: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include any caller-supplied `extra={...}` fields.
        for key, value in record.__dict__.items():
            if key not in self._RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for local development.

    Produces lines like:
        2026-07-08 14:32:01 | INFO     | ingestion.pdf_parser | Parsed 12 pages
    """

    _FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    _DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        """Initializes the formatter with the fixed console format string."""
        super().__init__(fmt=self._FORMAT, datefmt=self._DATE_FORMAT)


def _build_handlers(settings: LoggingSettings) -> list[logging.Handler]:
    """Builds the list of logging handlers based on configured settings.

    Args:
        settings: The validated `LoggingSettings` section.

    Returns:
        A list containing a stdout `StreamHandler`, and, if `log_file` is
        set, an additional `RotatingFileHandler`. Both handlers share the
        same formatter (JSON or console) determined by `settings.json_format`.
    """
    formatter: logging.Formatter = (
        JSONFormatter() if settings.json_format else ConsoleFormatter()
    )

    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    if settings.log_file is not None:
        log_path: Path = settings.log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path),
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    return handlers


def configure_logging(settings: Optional[LoggingSettings] = None, force: bool = False) -> None:
    """Configures the root logger for the entire application process.

    Idempotent by default: calling this more than once is a no-op unless
    `force=True`, which prevents duplicate handlers being attached if
    multiple entry points (e.g. `api/main.py` and a test fixture) both
    call it.

    Args:
        settings: An explicit `LoggingSettings` instance to use. If None,
            the value is pulled from `get_settings().logging`.
        force: When True, reconfigures the root logger even if
            `configure_logging` has already run in this process. Useful
            in pytest when a test needs a different log level.

    Returns:
        None.

    Example:
        >>> from config.logging import configure_logging
        >>> configure_logging()
    """
    global _CONFIGURED

    if _CONFIGURED and not force:
        return

    resolved_settings: LoggingSettings = settings or get_settings().logging

    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_settings.level)

    # Clear any pre-existing handlers to avoid duplicate log lines on
    # reconfiguration (relevant when force=True, e.g. in tests).
    for existing_handler in list(root_logger.handlers):
        root_logger.removeHandler(existing_handler)

    for handler in _build_handlers(resolved_settings):
        root_logger.addHandler(handler)

    # Quiet down noisy third-party libraries by default; individual
    # modules can still raise these back up via LOG_LEVEL if needed.
    for noisy_logger_name in ("httpx", "httpcore", "urllib3", "sentence_transformers"):
        logging.getLogger(noisy_logger_name).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger, configuring the root logger first if needed.

    This is the function every module in the codebase should call instead
    of `logging.getLogger()` directly, since it guarantees
    `configure_logging()` has run at least once (using default settings)
    even if the caller forgot to invoke it explicitly at startup.

    Args:
        name: The logger name, conventionally `__name__` of the calling
            module (e.g. "ingestion.pdf_parser").

    Returns:
        A configured `logging.Logger` instance.

    Example:
        >>> from config.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Started processing", extra={"document_id": "doc_123"})
    """
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
