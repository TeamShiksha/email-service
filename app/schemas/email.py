"""
Request and response schemas for email router.
"""
from email.policy import default
from typing import Optional, Dict, List
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo
from app.config import config
class SendEmailRequestBody(BaseModel):
    """
    Request body for sending emails.

    id: To identify which template to send
    subject: Subject for the email
    recipient: Recipient of the email
    body: Dynamic values which should be populated in
          the HTML template

    cc, bcc, and self are optional fields.
    """

    id: int
    subject: str
    recipient: Optional[EmailStr] = None
    body: Dict[str, str]
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    self: bool = False

    @field_validator("body")
    @classmethod
    def check_body_for_id(cls, body: dict, values: ValidationInfo) -> dict:
        """
        Validates if all the required keys are present for sending
        the email with all the required dynamic values.
        """
        data = values.data
        required_keys_map = {
            1: {"url"},
            2: {"url"},
            3: {"query", "response"},
            4: {"email", "magicLink"},
            5: {"name", "event", "dates", "venue", "badgeNumber", "ticketLink"},
            6: {"eventName", "updatesText", "updatesLink"},
            7: {"inviteeName", "eventName", "inviteText", "inviteLink"},
        }

        required_keys = required_keys_map.get(data.get("id"))
        if not required_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid id",
            )

        if not all(key in body for key in required_keys):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Key is missing from {required_keys}",
            )

        return body

    @field_validator("cc", "bcc", mode="before")
    @classmethod
    def add_self_to_recipients(cls, value, values: ValidationInfo):
        """
        Adds the sender's email to CC if self is True.
        """
        if values.data.get("self") and config.EMAIL_ADDRESS:
            if value is None:
                return [config.EMAIL_ADDRESS]
            elif config.EMAIL_ADDRESS not in value:
                value.append(config.EMAIL_ADDRESS)
        return value

    @field_validator("recipient", mode="before")
    @classmethod
    def validate_recipients(cls, value, values: ValidationInfo):
        """
        Ensures at least one recipient (recipient, cc, or bcc) is provided.
        """
        if not value and not values.data.get("cc") and not values.data.get("bcc"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one recipient (recipient, cc, or bcc) must be provided.",
            )
        return value
