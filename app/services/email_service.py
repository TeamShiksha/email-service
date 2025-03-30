"""
Third party email service configuration for sending emails.
"""

from smtplib import SMTPException, SMTPAuthenticationError, SMTPSenderRefused

import botocore.exceptions

from app.utils import EmailSender, SESEmailSender
from app.schemas.email import SendEmailRequestBody


class EmailService:
    """
    Service layer for handling email sending logic.
    """

    def __init__(self, email_sender: EmailSender, ses_email_sender: SESEmailSender):
        self.email_sender = email_sender
        self.ses_email_sender = ses_email_sender

    def send_email(self, email_details: SendEmailRequestBody, body: str):
        """
        Sends an email based on email details.

        Args:
            email_details (SendEmailRequestBody): Details for the email.
            body (str): body of the email.

        Returns:
            bool: True if no failure occurred on sending email.
        """
        try:
            result = self._send_email_by_provider(email_details, body)
            return result
        except Exception as e:
            self._handle_email_error(e)

    def _send_email_by_provider(self, email_details: SendEmailRequestBody, body: str):
        """
        Sends an email using the specified provider.

        Args:
            email_details (SendEmailRequestBody): Details for the email.
            body (str): body of the email.

        Returns:
            bool: True if no failure occurred on sending email.
        """
        if email_details.provider == "SES":
            return self.ses_email_sender.send_ses_email(
                to_email=email_details.recipient,
                subject=email_details.subject,
                body=body,
                cc=email_details.cc,
                bcc=email_details.bcc,
                is_html=True
            )
        elif email_details.provider == "GMAIL":
            return self.email_sender.send_email(
                to_email=email_details.recipient,
                subject=email_details.subject,
                body=body,
                cc=email_details.cc,
                bcc=email_details.bcc,
                is_html=True
            )
        else:
            raise ValueError(f"Unsupported email provider: {email_details.provider}")

    def _handle_email_error(self, error: Exception):
        """
        Handles errors that occur during email sending.

        Args:
            error (Exception): The exception raised during email sending.
        """
        if isinstance(error, SMTPAuthenticationError):
            raise PermissionError("Failed to authenticate with the SMTP server.") from error
        elif isinstance(error, SMTPSenderRefused):
            raise ValueError("Sender address refused by the SMTP server.") from error
        elif isinstance(error, SMTPException):
            raise ConnectionError(f"SMTP error occurred: {error}") from error
        elif isinstance(error, botocore.exceptions.ClientError):
            self._handle_aws_client_error(error)
        elif isinstance(error, botocore.exceptions.EndpointConnectionError):
            raise ConnectionError(f"Could not connect to AWS SES: {str(error)}") from error
        elif isinstance(error, botocore.exceptions.ParamValidationError):
            raise ValueError(f"Invalid parameters for AWS SES: {str(error)}") from error
        elif isinstance(error, botocore.exceptions.BotoCoreError):
            raise ConnectionError(f"AWS SES general error: {str(error)}") from error
        else:
            raise ConnectionError(f"Unexpected error when sending email: {str(error)}") from error

    def _handle_aws_client_error(self, error: botocore.exceptions.ClientError):
        """
        Handles AWS SES-specific client errors.

        Args:
            error (botocore.exceptions.ClientError): The exception raised by AWS SES.
        """
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']

        if error_code == 'MessageRejected':
            raise ValueError(f"AWS SES rejected the message: {error_message}") from error
        elif error_code == 'MailFromDomainNotVerified':
            raise ValueError(f"Sender domain not verified in AWS SES: {error_message}") from error
        elif error_code == 'ConfigurationSetDoesNotExist':
            raise ValueError(f"SES configuration issue: {error_message}") from error
        elif error_code in {'AccessDenied', 'InvalidClientTokenId', 'SignatureDoesNotMatch'}:
            raise PermissionError(f"AWS SES authentication error: {error_message}") from error
        elif error_code in {'ServiceUnavailable', 'Throttling'}:
            raise ConnectionError(f"AWS SES service issue: {error_message}") from error
        else:
            raise ConnectionError(f"AWS SES error: {error_code} - {error_message}") from error
