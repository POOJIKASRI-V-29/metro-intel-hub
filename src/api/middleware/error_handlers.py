"""Global exception handling middleware for the KMRL platform.

Scope: Catches unhandled exceptions, validation errors, and HTTP exceptions 
at the application level, converting them into a standardized JSON response 
structure for predictable frontend consumption.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.logging import get_logger
from src.utils.constants import ErrorCode

logger = get_logger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """Registers custom exception handlers to the FastAPI application instance.

    Args:
        app: The main FastAPI application instance.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handles expected HTTP exceptions raised deliberately in the routes."""
        logger.warning(f"HTTP Exception on {request.url.path}: {exc.detail}")
        
        # If the detail is already a dictionary (like we set up in upload.py), pass it through
        detail = exc.detail if isinstance(exc.detail, dict) else {
            "error_code": "HTTP_ERROR", 
            "message": str(exc.detail)
        }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handles Pydantic validation errors (e.g., missing fields, wrong types)."""
        logger.warning(f"Validation Error on {request.url.path}: {exc.errors()}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error_code": ErrorCode.VALIDATION_ERROR.value,
                "message": "The request payload failed structural validation.",
                "details": exc.errors()
            },
        )

    @app.exception_handler(Exception)
    async def global_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Acts as the ultimate catch-all for any unhandled server crashes."""
        logger.critical(f"Unhandled Server Crash on {request.url.path}: {repr(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error_code": ErrorCode.INTERNAL_ERROR.value,
                "message": "An unexpected internal server error occurred. The administrative team has been notified."
            },
        )