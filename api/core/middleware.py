import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

access_log = logging.getLogger("api.access")
error_log = logging.getLogger("api.error")


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """Log each request's method, path, status, and duration.

        Generates a short request ID, times the downstream call, logs the
        result to the access logger, and attaches the ID as an
        `X-Request-ID` response header.

        Args:
            request: The incoming request.
            call_next: Callable that invokes the next middleware/handler.

        Returns:
            The response produced by `call_next`, with the request ID header set.
        """
        request_id = str(uuid.uuid4())[:8]
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        access_log.info(
            "%s %s %s %dms id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


def register_exception_handlers(app: FastAPI) -> None:
    """Register a catch-all handler that logs and masks unhandled exceptions.

    Args:
        app: The FastAPI application to register the handler on.
    """

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Log an unhandled exception and return a generic 500 response.

        Args:
            request: The request being processed when the exception occurred.
            exc: The exception that was raised.

        Returns:
            A `JSONResponse` with status 500 and a generic error body.
        """
        error_log.exception("unhandled exception")
        return JSONResponse(status_code=500, content={"error": "internal server error"})
