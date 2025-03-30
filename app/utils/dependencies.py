"""
All the dependencies are defined here.
"""

from functools import wraps
from fastapi import HTTPException, Request
from app.config import config
from .email_sender import EmailSender, SESEmailSender


def require_authentication():
    """
    Decorator responsible for authentication check.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            auth_header = request.headers.get("Authorization")
            # Try to get the email type from the request body
            try:
                # Parse the request body
                body = await request.json()
                email_type = body.get("type", "NORMAL")
            except Exception:
                # If we can't parse the body or type is not specified, default to NORMAL
                email_type = "NORMAL"
        
            # Set app_secret based on email type
            if email_type == "SES":
                app_secret = config.AWS_SECRET_KEY
            else:  # NORMAL
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

def get_ses_email_sender() -> SESEmailSender:
    """
    Creates and returns an SESEmailSender object.
    This function is used as a dependency injection in the controller.
    """
    return SESEmailSender(
        aws_access_key=config.AWS_ACCESS_KEY,
        aws_secret_key=config.AWS_SECRET_KEY,
        aws_region=config.AWS_REGION,
        aws_email=config.AWS_EMAIL
    )
