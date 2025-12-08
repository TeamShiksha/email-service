"""
Third party email service configuration for sending emails.
"""

from typing import Dict, Union

from smtplib import SMTPException, SMTPAuthenticationError, SMTPSenderRefused
import botocore.exceptions

from app.utils import EmailSender, SESEmailSender
from app.schemas.email import SendEmailRequestBody, EmailProvider
import base64
import urllib.parse


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
            if email_details.id == 5 and 'iCalendarLink' in email_details.body:
                ics_content = self._extract_ics_from_data_url(
                    email_details.body.get('iCalendarLink', '')
                )
                if ics_content:
                    event_name = email_details.body.get('eventName', 'event')
                    result = self._send_email_with_ics_attachment(
                        email_details, body, event_name, ics_content
                    )
                    return result
            result = self._send_email_by_provider(email_details, body)
            return result
        except Exception as error:
            self._handle_email_error(error)

    def _extract_ics_from_data_url(self, data_url: str) -> str | None:
        """
        Extract ICS content from data URL.
        Handles formats like: data:text/calendar;charset=utf-8,BEGIN:VCALENDAR...
        """
        if not data_url or not data_url.startswith('data:'):
            return None

        try:
            header, data = data_url.split(',', 1)

            if 'base64' in header:
                decoded = base64.b64decode(data).decode('utf-8')
            else:
                decoded = urllib.parse.unquote(data)

            if decoded.strip().startswith('BEGIN:VCALENDAR'):
                return decoded
        except Exception as e:
            print(f"Error extracting ICS content: {e}")

        return None

    def _send_email_with_ics_attachment(
            self,
            email_details: SendEmailRequestBody,
            body: str,
            event_name: str,
            ics_content: str
    ):
        """
        Send email with ICS file as attachment.
        """
        provider = email_details.provider
        sender = self.email_sender.get(provider)

        # Sanitize filename
        safe_filename = ''.join(c for c in event_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_filename = safe_filename[:50] if safe_filename else 'event'
        filename = f"{safe_filename}.ics"

        # Check if sender supports attachments
        if hasattr(sender, 'send_email_with_attachment'):
            result = sender.send_email_with_attachment(
                to_email=email_details.recipient,
                subject=email_details.subject,
                body=body,
                cc=email_details.cc,
                bcc=email_details.bcc,
                is_html=True,
                attachment_content=ics_content,
                attachment_filename=filename,
                attachment_content_type='text/calendar'
            )
        else:
            # Fallback to regular email if attachment not supported
            print(f"Warning: {provider} sender doesn't support attachments, sending without ICS file")
            result = sender.send_email(
                to_email=email_details.recipient,
                subject=email_details.subject,
                body=body,
                cc=email_details.cc,
                bcc=email_details.bcc,
                is_html=True,
            )

        return result

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
