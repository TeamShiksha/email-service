"""
Request and response schemas for email router.
"""

from typing import Optional, Dict
from pydantic import BaseModel, EmailStr


class SendEmailRequestBody(BaseModel):
    """
    Request body for sending emails.

    id: To identify which template to send
    subject: Subject for the email
    recipient: Recipient of the email
    body: Dynamic values which should be populated in
            HTML template

    cc and bcc are optional field and can be used if required
    """

    id: int
    subject: str
    recipient: EmailStr
    body: Dict[str, str]
    cc: Optional[EmailStr] = None
    bcc: Optional[EmailStr] = None

class SendEmailResponseBody(BaseModel):
    """
    Response body for the send email API.
    """
    success: bool
    message: str
    details: SendEmailRequestBody
