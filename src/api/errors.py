"""Shared HTTP error builders for the KMRL Document Intelligence API."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.utils.constants import ErrorCode


def not_implemented(feature: str) -> HTTPException:
    """Build the 501 response for an endpoint whose backing feature does not exist yet.

    Used instead of returning placeholder data: a fabricated 200 is indistinguishable
    from a real answer, whereas a 501 lets callers (and the UI) say "not available".
    """
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "error_code": ErrorCode.NOT_IMPLEMENTED.value,
            "message": f"{feature} is not implemented yet."
        }
    )
