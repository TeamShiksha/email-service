"""
All the dependencies are defined here.
"""

from app.utils.email_sender import EmailSender
from app.config import config


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
