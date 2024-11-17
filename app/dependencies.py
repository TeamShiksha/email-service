"""
All the dependencies are defined here.
"""

from functools import wraps
from fastapi import HTTPException, Request
from app.utils.email_sender import EmailSender
from app.config import config


def require_authentication():
    """
    Decorator responsible for authentication check.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            auth_header = request.headers.get('Authorization')
            app_secret = config.APP_SECRET
            if not auth_header or auth_header != app_secret:
                raise HTTPException(status_code=401, detail="Unauthorized")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def get_email_sender() -> EmailSender:
    """
    Creates and returns an EmailSender object.
    This function is used as a dependency injection in the controller.
    """
    return EmailSender(
        smtp_server=config.EMAIL_HOST,
        smtp_port=config.EMAIL_PORT,
        username=config.EMAIL_ADDRESS,
        password=config.EMAIL_PASSWORD,
    )
