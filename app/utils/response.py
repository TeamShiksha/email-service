"""
Custom responses
"""

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(status_code: int = 200, message: str = "", body: dict = None):
    """
    Handles success response
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "details": jsonable_encoder(body),
        },
    )


def error_response(
    status_code: int = 500,
    message: str = "Something went wrong. Try again later.",
    body: dict = None,
):
    """
    Handles error response in a standardized format.
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "details": jsonable_encoder(body),
        },
    )
