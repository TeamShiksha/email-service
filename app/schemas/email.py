"""
Request and response schemas for email router.
"""

from typing import Optional, Dict
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo


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

    @field_validator("body")
    @classmethod
    def check_body_for_id(cls, body: dict, values: ValidationInfo) -> dict:
        """
        Validates if all the required keys are present for sending
        the email with all the required dynamic values.
        """
        data = values.data
        if data.get("id") == 1 or data.get("id") == 2:
            required_keys = {"url"}
            if not all(key in body for key in required_keys):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail= "Key is missing ['url']"
                )
        elif data.get("id") == 3:
            required_keys = {"query", "response"}
            if not all(key in body for key in required_keys):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail= "Key is missing out of ['query', 'response']"
                )
        else:
            raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail= "Invalid id"
                )
        return body

class SendEmailResponseBody(BaseModel):
    """
    Response body for the send email API.
    """
    success: bool
    message: str
    details: SendEmailRequestBody
