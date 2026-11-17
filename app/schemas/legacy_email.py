"""
Request schema for the legacy POST /email endpoint, and its translation
into a NotificationRequest.

Existing callers (openlogo, rsvp, team.shiksha, swags.me) send this shape
with a numeric template id. It stays accepted as-is; new integrations
should use POST /v1/notifications.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.config import config
from app.notifications import templates
from app.notifications.errors import InvalidRequestError
from app.notifications.models import Channel, NotificationRequest, Recipient


class EmailProvider(str, Enum):
    """Email providers callers may name."""

    GMAIL = "GMAIL"
    SES = "SES"
    AUTOSEND = "AUTOSEND"


class SendEmailRequestBody(BaseModel):
    """
    Request body for POST /email.

    id:        Numeric template id (see GET /v1/templates for the mapping).
    subject:   Subject for the email.
    recipient: Main recipient.
    body:      Values for the template.
    cc:        Visible copies on the main recipient's email.
    bcc:       Each address receives its own copy of the email. Nobody is
               blind-copied any more, and recipients still cannot see each other.
    self:      Also send a copy to the service's sender address.
    """

    id: int
    subject: str
    recipient: Optional[EmailStr] = None
    body: Dict[str, Any] = Field(default_factory=dict)
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    self: bool = False
    provider: Optional[EmailProvider] = None


def to_notification_request(email: SendEmailRequestBody) -> NotificationRequest:
    """
    Translates a legacy request into one message per recipient:

    - `recipient` gets the email with `cc` visible on it. With no
      recipient, the first cc takes its place (cc is visible anyway).
    - every `bcc` address gets its own email.
    - `self` adds a copy to the configured sender address.
    """
    definition = templates.get_template_by_legacy_id(email.id)

    cc = [str(c) for c in email.cc or []]
    primary = str(email.recipient) if email.recipient else None
    if primary is None and cc:
        primary, cc = cc[0], cc[1:]

    recipients: List[Recipient] = []
    already_copied = set()
    if primary:
        recipients.append(Recipient(to=primary, cc=cc))
        already_copied = {primary.lower(), *(c.lower() for c in cc)}

    extra = [str(b) for b in email.bcc or []]
    if email.self and config.EMAIL_ADDRESS:
        extra.append(config.EMAIL_ADDRESS)
    recipients.extend(Recipient(to=b) for b in extra if b.lower() not in already_copied)

    if not recipients:
        raise InvalidRequestError(
            "At least one recipient (recipient, cc, or bcc) must be provided."
        )

    return NotificationRequest(
        template=definition.key,
        channel=Channel.EMAIL,
        provider=email.provider.value if email.provider else None,
        recipients=recipients,
        data=email.body,
        subject=email.subject,
    )
