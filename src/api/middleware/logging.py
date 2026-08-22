"""Request tracing and logging middleware for the KMRL platform.

Scope: Intercepts all incoming HTTP requests to assign a unique request ID, 
measure processing latency, and log standard access details (method, path, 
status code) to aid in debugging and telemetry collection.
"""

from __future__ import annotations

import time
import uuid
from typing import Callable, Awaitable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config.logging import get_logger

logger = get_logger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware to trace requests and log processing latency."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Processes the request, tracks execution time, and injects a Request ID.

        Args:
            request: The incoming FastAPI request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The standard HTTP response, appended with custom tracking headers.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Attach the request ID to the request state so routes can access it if needed
        request.state.request_id = request_id

        start_time = time.perf_counter()
        
        logger.debug(f"Incoming Request: {request.method} {request.url.path} [ID: {request_id}]")

        try:
            response = await call_next(request)
        except Exception as exc:
            # We log the crash here, but let the global exception handler format the output
            process_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request FAILED: {request.method} {request.url.path} "
                f"[ID: {request_id}] in {process_time_ms:.2f}ms. Reason: {exc}"
            )
            raise

        process_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Request Completed: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Latency: {process_time_ms:.2f}ms [ID: {request_id}]"
        )

        # Inject telemetry headers into the response for the frontend/gateway
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"

        return response