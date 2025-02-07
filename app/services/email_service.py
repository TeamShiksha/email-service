"""
Third party email service configuration for sending emails.
"""

from smtplib import SMTPException, SMTPAuthenticationError, SMTPSenderRefused
from app.utils.email_sender import EmailSender
from app.schemas.email import SendEmailRequestBody


class EmailService:
    """
    Service layer for handling email sending logic.
    """

    def __init__(self, email_sender: EmailSender):
        self.email_sender = email_sender

    def send_email(self, email_details: SendEmailRequestBody, body: str):
        """
        Sends an email based on email details.

        Args:
            email_details (SendEmailRequestBody): Details for the email.
            body (str): body of the email.

        Returns:
            bool: True if no failure occured on sending email.
        """
        try:
            result = self.email_sender.send_email(
                to_email=email_details.recipient,
                subject=email_details.subject,
                cc=email_details.cc,
                bcc=email_details.bcc,
                body=body,
                cc=email_details.cc,
                bcc=email_details.bcc,
                is_html=True,
            )
            return result
        except SMTPAuthenticationError as exc:
            raise PermissionError(
                "Failed to authenticate with the SMTP server."
            ) from exc
        except SMTPSenderRefused as exc:
            raise ValueError("Sender address refused by the SMTP server.") from exc
        except SMTPException as smtp_exc:
            raise ConnectionError(f"SMTP error occurred: {smtp_exc}") from smtp_exc
