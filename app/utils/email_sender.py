"""
For third party email sender.
"""

import base64
import smtplib
import boto3
import requests
from email.message import EmailMessage
from typing import List, Optional

from pydantic import EmailStr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication


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
        self.ses_client = boto3.client(
            "ses",
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
        )

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
            response = self.ses_client.send_email(
                Source=self.aws_email, Destination=destination, Message=message
            )
            return {"success": True, "message_id": response["MessageId"]}
        except Exception as error:
            raise ConnectionError(f"Email sending failed: {str(error)}") from error

    def send_email_with_attachment(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_content: str,
        attachment_filename: str,
        attachment_content_type: str = 'application/octet-stream',
        cc: List[EmailStr] = None,
        bcc: List[EmailStr] = None,
        is_html: bool = True,
    ) -> dict:
        """
        Sends an email with an attachment (like an ICS file) using AWS SES send_raw_email.
        """
        try:
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.aws_email
            msg['To'] = to_email

            if cc:
                msg['Cc'] = ", ".join(cc)
            if bcc:
                msg['Bcc'] = ", ".join(bcc)

            body_type = 'html' if is_html else 'plain'
            msg.attach(MIMEText(body, body_type))

            if isinstance(attachment_content, str):
                attachment_data = attachment_content.encode('utf-8')
            else:
                attachment_data = attachment_content

            part = MIMEApplication(attachment_data)
            
            part.add_header(
                'Content-Disposition', 
                'attachment', 
                filename=attachment_filename
            )
            
            if attachment_content_type:
                part.add_header('Content-Type', attachment_content_type)

            msg.attach(part)

            destinations = [to_email]
            if cc:
                destinations.extend(cc)
            if bcc:
                destinations.extend(bcc)

            response = self.ses_client.send_raw_email(
                Source=self.aws_email,
                Destinations=destinations,
                RawMessage={
                    'Data': msg.as_string(),
                }
            )
            return {'success': True, 'message_id': response['MessageId']}

        except Exception as error:
            raise ConnectionError(f"Email with attachment failed: {str(error)}") from error


class AutosendEmailSender:
    """
    A helper class for sending emails using the Autosend REST API.

    Mirrors the interface of SESEmailSender so the service layer can swap
    between providers without changes. See https://docs.autosend.com/.
    """

    def __init__(
        self,
        api_key: str,
        from_email: str,
        from_name: str = "",
        base_url: str = "https://api.autosend.com/v1",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _sender(self) -> dict:
        sender = {"email": self.from_email}
        if self.from_name:
            sender["name"] = self.from_name
        return sender

    @staticmethod
    def _as_recipients(emails: Optional[List[EmailStr]]) -> List[dict]:
        return [{"email": str(email)} for email in emails or []]

    def _build_destination(
        self,
        to_email: Optional[str],
        cc: Optional[List[EmailStr]],
        bcc: Optional[List[EmailStr]],
    ) -> dict:
        """
        Builds the to/cc/bcc portion of the payload.

        Autosend requires a `to` recipient, while SES accepted a cc/bcc-only
        send. When there is no recipient the first cc is promoted, since cc is
        already visible to everyone; a bcc is never promoted as that would
        expose a blind recipient.
        """
        cc_list = self._as_recipients(cc)
        bcc_list = self._as_recipients(bcc)

        if to_email:
            to = {"email": str(to_email)}
        elif cc_list:
            to = cc_list.pop(0)
        else:
            to = self._sender()

        destination = {"to": to}
        if cc_list:
            destination["cc"] = cc_list
        if bcc_list:
            destination["bcc"] = bcc_list
        return destination

    def _post(self, payload: dict) -> dict:
        try:
            response = requests.post(
                f"{self.base_url}/mails/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise ConnectionError(f"Email sending failed: {str(error)}") from error

        if response.status_code in (401, 403):
            raise PermissionError(
                f"Authentication failed: {response.status_code} {response.text}"
            )
        if response.status_code >= 400:
            raise ConnectionError(
                f"Email sending failed: {response.status_code} {response.text}"
            )

        data = response.json().get("data", {})
        return {"success": True, "message_id": data.get("emailId")}

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: List[EmailStr],
        bcc: List[EmailStr],
        is_html: bool = False,
    ) -> dict:
        payload = {
            "from": self._sender(),
            "subject": subject,
            **self._build_destination(to_email, cc, bcc),
        }
        payload["html" if is_html else "text"] = body
        return self._post(payload)

    def send_email_with_attachment(
        self,
        to_email: str,
        subject: str,
        body: str,
        attachment_content: str,
        attachment_filename: str,
        attachment_content_type: str = "application/octet-stream",
        cc: List[EmailStr] = None,
        bcc: List[EmailStr] = None,
        is_html: bool = True,
    ) -> dict:
        """
        Sends an email with an attachment (like an ICS file) using Autosend.
        """
        if isinstance(attachment_content, str):
            attachment_data = attachment_content.encode("utf-8")
        else:
            attachment_data = attachment_content

        payload = {
            "from": self._sender(),
            "subject": subject,
            "attachments": [
                {
                    "fileName": attachment_filename,
                    "content": base64.b64encode(attachment_data).decode("utf-8"),
                    "contentType": attachment_content_type,
                }
            ],
            **self._build_destination(to_email, cc, bcc),
        }
        payload["html" if is_html else "text"] = body
        return self._post(payload)
