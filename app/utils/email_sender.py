"""
For third party email sender.
"""

import smtplib
import boto3
from email.message import EmailMessage
from typing import List

from pydantic import EmailStr


class EmailSender:
    """
    A helper class to handle email sending functionality via SMTP.

    This class provides methods for sending plain text and HTML emails, configured
    with SMTP server credentials.

    Attributes:
        smtp_server (str): The SMTP server address.
        smtp_port (int): The SMTP server port.
        username (str): Username for SMTP server authentication.
        password (str): Password for SMTP server authentication.
    """

    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        """
        Initializes the EmailSender instance with the given
        SMTP server details and credentials.

        Args:
            smtp_server (str): The address of the SMTP server.
            smtp_port (int): The port of the SMTP server.
            username (str): The username used for authenticating with the SMTP server.
            password (str): The password used for authenticating with the SMTP server.
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = True

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: List[EmailStr],
        bcc: List[EmailStr],
        is_html: bool = False,
    ) -> dict:
        """
        Sends an email using the configured SMTP settings.

        Args:
            to_email (str): The recipient's email address.
            subject (str): The subject line of the email.
            body (str): The body of the email, which can be in plain text or HTML.
            is_html (bool, optional): Specifies whether the email body is HTML content.
                                      Defaults to False.
        Returns:
            dict: A response dictionary containing:
                - "success" (bool): Indicates whether the email was sent successfully.
                - "error": Error message if the email sending fails.

        Raises:
            Exception: If there is an error during the email-sending process,
                       an exception is raised and the error message is included in the response.
        """
        try:
            msg = EmailMessage()
            msg["From"] = self.username
            msg["To"] = to_email
            msg["Subject"] = subject
            if cc:
                msg["Cc"] = ",".join(cc)
            if bcc:
                msg["Bcc"] = ",".join(bcc)
            msg.add_alternative(body, subtype="html" if is_html else "plain")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            return {"success": True}
        except Exception as error:
            raise ConnectionError(f"Email sending failed: {str(error)}") from error


class SESEmailSender:
    """
    A helper class for sending emails using AWS SES.

    This class provides methods for sending emails through Amazon Simple Email Service (SES).
    """

    def __init__(
        self, aws_access_key: str, aws_secret_key: str, aws_region: str, aws_email: str
    ):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region
        self.aws_email = aws_email

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: List[EmailStr],
        bcc: List[EmailStr],
        is_html: bool = False,
    ) -> dict:
        try:
            ses_client = boto3.client(
                "ses",
                region_name=self.aws_region,
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
            )
            message = {"Subject": {"Data": subject}, "Body": {}}
            if is_html:
                message["Body"]["Html"] = {"Data": body}
            else:
                message["Body"]["Text"] = {"Data": body}
            destination = {
                "ToAddresses": [to_email] if to_email else [],
            }
            if cc:
                destination["CcAddresses"] = cc
            if bcc:
                destination["BccAddresses"] = bcc
            response = ses_client.send_email(
                Source=self.aws_email, Destination=destination, Message=message
            )
            return {"success": True, "message_id": response["MessageId"]}
        except Exception as error:
            raise ConnectionError(f"Email sending failed: {str(error)}") from error
