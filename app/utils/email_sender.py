"""
For third party email sender.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic import EmailStr
from typing import List


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
            self, to_email: EmailStr, subject: str, body: str,  cc: List[EmailStr], bcc: List[EmailStr], is_html: bool = False,
    ) -> bool:
        """
        Sends an email using the configured SMTP settings.
        """
        try:
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = self.username
            msg["To"] = to_email

            if cc:
                msg["Cc"] = ", ".join(cc)

            bcc_recipients = bcc or []

            msg.attach(MIMEText(body, "html" if is_html else "plain"))

            recipients = [msg["To"]] + msg.get_all("Cc", []) + bcc_recipients

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(msg["From"], recipients, msg.as_string())
            return {"success": True}
        except Exception as e:
            raise e
