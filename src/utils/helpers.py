"""Generic, cross-cutting utility functions for the KMRL platform.

Scope is intentionally narrow: retry/backoff, safe JSON extraction from
LLM text output, ID generation, and execution timing. File-specific,
text-specific, and embedding-specific helpers live in their own modules
(`file_utils.py`, `text_utils.py`, `embedding_utils.py`) to keep this
file small and avoid duplicate homes for the same kind of logic.
"""

from __future__ import annotations

import functools
import json
import re
import time
import uuid
from typing import Any, Callable, Optional, Type, TypeVar

from config.logging import get_logger

logger = get_logger(__name__)

_T = TypeVar("_T")

_JSON_OBJECT_OR_ARRAY_PATTERN = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay_seconds: float = 1.0,
    backoff_multiplier: float = 2.0,
    exceptions: tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., _T]], Callable[..., _T]]:
    """Decorates a function to retry on failure with exponential backoff.

    Intended for flaky I/O calls (LLM providers, Neo4j, ChromaDB, OCR
    engines) where a transient failure is likely to succeed on retry.

    Args:
        max_attempts: Maximum number of attempts before giving up and
            re-raising the last exception.
        initial_delay_seconds: Delay before the first retry.
        backoff_multiplier: Multiplier applied to the delay after each
            failed attempt (e.g. 1s, 2s, 4s for multiplier=2.0).
        exceptions: Tuple of exception types that should trigger a retry.
            Exceptions not in this tuple propagate immediately.

    Returns:
        A decorator that wraps the target function with retry behavior.

    Example:
        >>> @retry_with_backoff(max_attempts=3, exceptions=(ConnectionError,))
        ... def call_llm():
        ...     ...
    """

    def decorator(func: Callable[..., _T]) -> Callable[..., _T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> _T:
            delay = initial_delay_seconds
            last_exception: Optional[BaseException] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts:
                        logger.error(
                            "Function %s failed after %d attempts: %s",
                            func.__name__, attempt, exc,
                        )
                        raise
                    logger.warning(
                        "Function %s failed on attempt %d/%d: %s. Retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, delay,
                    )
                    time.sleep(delay)
                    delay *= backoff_multiplier

            # Unreachable in practice; satisfies type checkers.
            assert last_exception is not None
            raise last_exception

        return wrapper

    return decorator


def extract_json_from_text(raw_text: str) -> Any:
    """Extracts and parses the first JSON object or array found in free text.

    LLMs frequently wrap JSON output in markdown code fences or add
    prose before/after the actual JSON payload. This function strips
    fences and locates the first `{...}` or `[...]` block before parsing,
    rather than assuming the entire string is valid JSON.

    Args:
        raw_text: The raw text returned by an LLM, potentially containing
            markdown fences or surrounding commentary.

    Returns:
        The parsed JSON value (dict, list, etc.).

    Raises:
        ValueError: If no JSON object/array can be located in the text,
            or if the located substring fails to parse as valid JSON.

    Example:
        >>> extract_json_from_text('Here is the result:\\n```json\\n{"a": 1}\\n```')
        {'a': 1}
    """
    cleaned_text = raw_text.strip()
    cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
    cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass

    match = _JSON_OBJECT_OR_ARRAY_PATTERN.search(cleaned_text)
    if not match:
        raise ValueError(f"No JSON object or array found in text: {raw_text!r}")

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse extracted JSON: {exc}") from exc


def generate_id(prefix: Optional[str] = None) -> str:
    """Generates a unique identifier, optionally namespaced with a prefix.

    Args:
        prefix: Optional short string prepended to the UUID (e.g. "doc",
            "chunk", "job"), separated by an underscore.

    Returns:
        A string like "doc_3f9a1c2e4b7d4e1a9c8f6b2d1e0a5c3f" if a prefix
        is given, or a bare UUID4 hex string otherwise.

    Example:
        >>> generate_id("doc")  # doctest: +SKIP
        'doc_3f9a1c2e4b7d4e1a9c8f6b2d1e0a5c3f'
    """
    unique_part = uuid.uuid4().hex
    return f"{prefix}_{unique_part}" if prefix else unique_part


class Timer:
    """Context manager for measuring elapsed wall-clock time of a code block.

    Attributes:
        elapsed_seconds: Populated after the `with` block exits; `None`
            beforehand.
    """

    def __init__(self) -> None:
        """Initializes the timer with no recorded elapsed time yet."""
        self._start_time: Optional[float] = None
        self.elapsed_seconds: Optional[float] = None

    def __enter__(self) -> "Timer":
        """Starts the timer.

        Returns:
            This `Timer` instance, so `elapsed_seconds` can be read after
            the `with` block via the original reference.
        """
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Stops the timer and records the elapsed duration.

        Args:
            *exc_info: Standard context-manager exception info tuple
                (type, value, traceback), unused here since the timer
                records elapsed time regardless of whether an exception
                occurred inside the block.
        """
        assert self._start_time is not None
        self.elapsed_seconds = time.perf_counter() - self._start_time


def truncate_for_log(value: str, max_length: int = 200) -> str:
    """Truncates a string for safe, readable inclusion in log messages.

    Prevents accidentally logging entire document bodies or LLM responses
    at full length, which can bloat log storage and obscure the actual
    log line of interest.

    Args:
        value: The string to truncate.
        max_length: Maximum number of characters to retain before adding
            a truncation marker.

    Returns:
        The original string if it's within `max_length`, otherwise the
        truncated string with a "... [truncated, N chars total]" suffix.

    Example:
        >>> truncate_for_log("a" * 500, max_length=10)
        'aaaaaaaaaa... [truncated, 500 chars total]'
    """
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}... [truncated, {len(value)} chars total]"