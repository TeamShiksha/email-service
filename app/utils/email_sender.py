"""
For third party email sender.
"""

import smtplib
import boto3
from email.message import EmailMessage
from typing import List

from pydantic import EmailStr

from app.config import config


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
        self.config = config

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: List[EmailStr],
        bcc: List[EmailStr],
        is_html: bool = False,
        type: str = "NORMAL"
    ) -> bool:
        """
        Sends an email using the configured SMTP settings.

        Args:
            to_email (str): The recipient's email address.
            subject (str): The subject line of the email.
            body (str): The body of the email, which can be in plain text or HTML.
            is_html (bool, optional): Specifies whether the email body is HTML content.
                                      Defaults to False.
            type (str): Email sent using SES or Normal SMTP.

        Returns:
            dict: A response dictionary containing the success of the email send action.

        Raises:
            Exception: If there is an error during the email-sending process,
                       an exception is raised and the error message is included in the response.
        """
        try:
            if type == "SES":
                
                ses_client = boto3.client(
                    "ses",
                    region_name=self.config.AWS_REGION,
                    aws_access_key_id=self.config.AWS_ACCESS_KEY,
                    aws_secret_access_key=self.config.AWS_SECRET_KEY
                )
                
                message = {
                    'Subject': {'Data': subject},
                    'Body': {}
                }
                
                if is_html:
                    message['Body']['Html'] = {'Data': body}
                else:
                    message['Body']['Text'] = {'Data': body}
                
                destination = {
                    'ToAddresses': [to_email] if to_email else [],
                }
                
                if cc:
                    destination['CcAddresses'] = cc
                
                if bcc:
                    destination['BccAddresses'] = bcc
                
                
                # Send email using SES
                response = ses_client.send_email(
                    Source=self.config.EMAIL_ADDRESS,
                    Destination=destination,
                    Message=message
                )
                
                print(f"Email sent via SES with message ID: {response['MessageId']}")
                return True
            
            elif type == "NORMAL":
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
        
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            raise e