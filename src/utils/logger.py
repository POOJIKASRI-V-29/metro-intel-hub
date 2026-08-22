"""Utility logging extensions for the KMRL platform.

Scope: Provides reusable decorators and structured event loggers for 
performance telemetry (timing) and security auditing across pipelines.
"""

from __future__ import annotations

import time
import json
from functools import wraps
from typing import Any, Callable, Dict

# Import the base configuration we built earlier
from config.logging import get_logger

# Initialize the utility logger
logger = get_logger(__name__)


def log_execution_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to measure and log the execution time of any function.
    
    Highly useful for tracking pipeline bottlenecks (e.g., OCR or LLM latency).

    Args:
        func: The target function or pipeline to measure.

    Returns:
        The wrapped function with injected timing telemetry.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        logger.debug(f"Starting execution of '{func.__name__}'...")
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            logger.info(f"Function '{func.__name__}' completed in {elapsed_time:.4f} seconds.")
            
    return wrapper


def log_audit_event(action: str, user_id: str, details: Dict[str, Any]) -> None:
    """Logs a structured security or operational event for compliance tracking.

    Args:
        action: The name of the event (e.g., "DOCUMENT_UPLOAD", "RAG_QUERY").
        user_id: The identifier of the user triggering the action.
        details: A dictionary of context (e.g., filename, query text).
    """
    audit_payload = {
        "event_type": "AUDIT",
        "action": action,
        "user_id": user_id,
        "details": details,
        "timestamp": time.time()
    }
    # Using JSON dumps ensures the payload can be easily parsed by log aggregators
    logger.info(f"AUDIT EVENT: {json.dumps(audit_payload)}")