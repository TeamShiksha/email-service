"""
All custom exception hanlders.
"""

from fastapi import HTTPException, Request
from app.utils.response import error_response


async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom handler for HTTP exceptions to ensure a uniform error response format.
    """
    return error_response(
        status_code=exc.status_code,
        message=exc.detail if isinstance(exc.detail, str) else "An error occurred.",
        body=exc.detail if isinstance(exc.detail, dict) else None,
    )


async def custom_general_exception_handler():
    """
    Custom handler for unanticipated exceptions.
    """
    return error_response(
        status_code=500, message="Something went wrong. Try again later.", body=None
    )
