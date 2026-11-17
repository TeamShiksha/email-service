"""
Exception handlers that keep every error in the standard envelope.
"""

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from app.core.responses import error_response, status_for_error
from app.notifications.errors import NotificationError

logger = logging.getLogger(__name__)


async def http_exception_handler(_request: Request, exc: HTTPException):
    """HTTP exceptions raised by routes and dependencies."""
    return error_response(
        status_code=exc.status_code,
        message=exc.detail if isinstance(exc.detail, str) else "An error occurred.",
        body=exc.detail if isinstance(exc.detail, dict) else None,
    )


async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    """Request bodies that fail schema validation."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    message = first.get("msg", "Invalid request.")
    if location:
        message = f"{location}: {message}"
    return error_response(
        status_code=422,
        message=message,
        body=[{"loc": e.get("loc"), "msg": e.get("msg")} for e in errors],
    )


async def notification_exception_handler(_request: Request, exc: NotificationError):
    """Errors from the notification layer."""
    code = status_for_error(exc)
    if code >= 500:
        logger.error("Notification failed: %s", exc)
    return error_response(status_code=code, message=str(exc))


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Anything unexpected."""
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return error_response(status_code=500)
