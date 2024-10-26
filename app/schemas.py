"""
For pydantic request and response schemas
"""

from typing import Optional, Dict
from pydantic import BaseModel, EmailStr


class SendEmailRequestBody(BaseModel):
    """
    Request body for sending emails.

    id: To identify which template to send
    subject: Subject for the email
    recipient: Recipient of the email
    values: Dynamic values which should be populated in
            HTML template

    cc and bcc are optional field and can be used if required
    """

    id: int
    subject: str
    recipient: EmailStr
    values: Dict[str, str]
    cc: Optional[EmailStr] = None
    bcc: Optional[EmailStr] = None

    # add validation based on ID, exmaple: forgot password requried 1 value
    # Example: forgot password link
    # On the otherhand welcome message might require 2 value
    # Example: name, date of registeration


class SendEmailResponseBody(BaseModel):
    """
    Model for sending response

    status_code: response status code
    message: String message if any
    content: details if any, used for error details
    error: error message
    """
    status_code: int
    message: str
    content: Optional[Dict] = None
    error: Optional[str] = None
