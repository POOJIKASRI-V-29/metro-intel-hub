"""Request body size limit for the upload endpoint.

Starlette parses (and spools to disk) a multipart body before any route code runs, so a
size check inside the handler fires only after the whole upload has been received. This
pure-ASGI middleware rejects an oversize request from its ``Content-Length`` header, and
counts bytes as they stream in for clients that send no length.
"""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from config.logging import get_logger
from src.utils.constants import ErrorCode

logger = get_logger(__name__)


class _BodyTooLarge(Exception):
    """Raised from the receive channel once the streamed body passes the limit."""


class MaxBodySizeMiddleware:
    """Reject POSTs to one path whose request body exceeds ``max_bytes`` with a 413."""

    def __init__(self, app: ASGIApp, path: str, max_bytes: int) -> None:
        self.app = app
        self.path = path
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != self.path:
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            logger.warning(f"Rejected upload: declared Content-Length {int(declared)} exceeds {self.max_bytes}.")
            await self._reject(scope, receive, send)
            return

        received = 0
        exceeded = False
        reject_sent = False

        async def reject_once() -> None:
            nonlocal reject_sent
            if not reject_sent:
                reject_sent = True
                await self._reject(scope, receive, send)

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Message) -> None:
            # FastAPI turns any exception raised while parsing the body into its own 400
            # response, which would hide ours. Once the limit has tripped, discard whatever
            # the app tries to send and answer with the 413 instead.
            if exceeded:
                await reject_once()
                return
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            pass
        if exceeded:
            logger.warning(f"Rejected upload: streamed body exceeded {self.max_bytes} bytes.")
            await reject_once()

    async def _reject(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit_mb = self.max_bytes / (1024 * 1024)
        response = JSONResponse(
            status_code=413,
            content={
                "detail": {
                    "error_code": ErrorCode.FILE_TOO_LARGE.value,
                    "message": f"Request body exceeds the maximum permitted size of {limit_mb:.0f} MB.",
                }
            },
        )
        await response(scope, receive, send)
