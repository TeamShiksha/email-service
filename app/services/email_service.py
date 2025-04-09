"""
Third party email service configuration for sending emails.
"""

from typing import Dict, Union

from smtplib import SMTPException, SMTPAuthenticationError, SMTPSenderRefused
import botocore.exceptions

from app.utils import EmailSender, SESEmailSender
from app.schemas.email import SendEmailRequestBody, EmailProvider


class EmailService:
    """
    Service layer for handling email sending logic.
    """

    def __init__(
        self, email_sender: Dict[EmailProvider, Union[EmailSender, SESEmailSender]]
    ):
        self.email_sender = email_sender

    def send_email(self, email_details: SendEmailRequestBody, body: str):
        """
        Sends an email based on email details.
        Args:
            email_details (SendEmailRequestBody): Details for the email.
            body (str): body of the email.

        Returns:
            dict: A response dictionary containing:
                - "success" (bool): Indicates whether the email was sent successfully.
                - "error": Error message if the email sending fails.
        """
        try:
            result = self._send_email_by_provider(email_details, body)
            return result
        except Exception as error:
            self._handle_email_error(error)

    def _send_email_by_provider(self, email_details: SendEmailRequestBody, body: str):
        provider = email_details.provider
        sender = self.email_sender.get(provider)
        result = sender.send_email(
            to_email=email_details.recipient,
            subject=email_details.subject,
            body=body,
            cc=email_details.cc,
            bcc=email_details.bcc,
            is_html=True,
        )
        return result

    def _handle_email_error(self, error: Exception):
        if isinstance(
            error, (SMTPAuthenticationError, botocore.exceptions.ClientError)
        ):
            raise PermissionError(f"Authentication failed: {str(error)}") from error
        elif isinstance(error, SMTPSenderRefused):
            raise ValueError(f"Email address refused: {str(error)}") from error
        else:
            raise ConnectionError(f"Email sending failed: {str(error)}") from error
