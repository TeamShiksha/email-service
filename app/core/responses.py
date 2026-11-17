"""
Response envelope shared by every endpoint:
{"success": bool, "message": str, "details": ...}
"""

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.notifications.errors import (
    DeliveryError,
    InvalidRequestError,
    NotificationError,
    ProviderAuthError,
    ProviderNotConfiguredError,
    TemplateNotFoundError,
)
from app.notifications.models import NotificationResult


def success_response(status_code: int = 200, message: str = "", body: Any = None, **extra):
    """Handles success response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "details": jsonable_encoder(body),
            **jsonable_encoder(extra),
        },
    )


def error_response(
    status_code: int = 500,
    message: str = "Something went wrong. Try again later.",
    body: Any = None,
    **extra,
):
    """Handles error response in a standardized format."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "details": jsonable_encoder(body),
            **jsonable_encoder(extra),
        },
    )


_ERROR_STATUS = (
    (TemplateNotFoundError, 404),
    (InvalidRequestError, 422),
    (ProviderNotConfiguredError, 503),
    (ProviderAuthError, 502),
    (DeliveryError, 502),
)


def status_for_error(error: NotificationError) -> int:
    """HTTP status for a notification error."""
    for error_type, code in _ERROR_STATUS:
        if isinstance(error, error_type):
            return code
    return 500


def status_for_result(result: NotificationResult) -> int:
    """
    200 when every recipient was sent to, 207 when only some were, 502
    when none were.

    A partial send must stay 2xx: callers that retry on errors would
    otherwise resend to the people who already received it.
    """
    if result.failed == 0:
        return 200
    if result.sent > 0:
        return 207
    return 502


def message_for_result(result: NotificationResult) -> str:
    """Human-readable summary of a result."""
    if result.failed == 0:
        return "Success"
    if result.sent > 0:
        return f"Partially delivered: {result.failed} of {result.total} failed."
    return "Delivery failed for every recipient."


def result_response(result: NotificationResult, body: Any = None, **extra) -> JSONResponse:
    """
    Envelope for a delivery result. `success` is true only when every
    recipient was sent to. `body` defaults to the result itself.
    """
    build = success_response if result.failed == 0 else error_response
    return build(
        status_code=status_for_result(result),
        message=message_for_result(result),
        body=result if body is None else body,
        **extra,
    )
