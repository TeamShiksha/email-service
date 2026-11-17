"""
Channel-agnostic request and result models for notifications.
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class Channel(str, Enum):
    """
    Delivery channels. Only EMAIL has providers today; the others are
    reserved so callers and templates can target them once providers exist.
    """

    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"


class Attachment(BaseModel):
    """
    A file attached to an email. `content` is raw bytes.
    """

    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


class Recipient(BaseModel):
    """
    One recipient. Each recipient receives their own message.

    to:   Address on the chosen channel (email address, E.164 phone number,
          or device token).
    data: Template variables for this recipient only. They override the
          request-level `data`, so messages can be personalised.
    cc:   Email only. Addresses copied visibly on THIS recipient's message,
          e.g. an interviewer on an interview confirmation. Never use cc to
          reach an audience; add them as recipients instead.
    """

    to: str
    data: Dict[str, Any] = Field(default_factory=dict)
    cc: List[EmailStr] = Field(default_factory=list)


class NotificationRequest(BaseModel):
    """
    Request body for POST /v1/notifications.
    """

    template: str = Field(
        description="Template key, e.g. `rsvp.update`. See GET /v1/templates."
    )
    channel: Channel = Channel.EMAIL
    provider: Optional[str] = Field(
        default=None,
        description="Provider name, e.g. `AUTOSEND`. Defaults to the configured provider.",
    )
    recipients: List[Recipient] = Field(min_length=1)
    data: Dict[str, Any] = Field(
        default_factory=dict, description="Template variables shared by every recipient."
    )
    subject: Optional[str] = Field(
        default=None, description="Email subject. Falls back to the template default."
    )
    reply_to: Optional[EmailStr] = None


class DeliveryResult(BaseModel):
    """
    Outcome for a single recipient.
    """

    to: str
    status: Literal["sent", "failed"]
    message_id: Optional[str] = None
    error: Optional[str] = None


class NotificationResult(BaseModel):
    """
    Outcome of a whole request.
    """

    template: str
    channel: Channel
    provider: str
    total: int
    sent: int
    failed: int
    results: List[DeliveryResult]
    warnings: List[str] = Field(default_factory=list)
