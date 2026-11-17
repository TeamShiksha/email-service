"""
The email message every email provider sends.
"""

from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr
from typing import List, Optional

from app.notifications.models import Attachment


@dataclass
class EmailMessage:
    """
    One email to one recipient, plus optional visible cc's.

    There is deliberately no bcc: an audience is sent as one message per
    recipient instead of one message with a hidden recipient list.
    """

    to: str
    subject: str
    html: str
    cc: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None
    attachments: List[Attachment] = field(default_factory=list)


def to_mime(message: EmailMessage, sender: str, sender_name: str = "") -> MimeMessage:
    """Builds a MIME message for SMTP and SES raw sends."""
    mime = MimeMessage()
    mime["From"] = formataddr((sender_name, sender)) if sender_name else sender
    mime["To"] = message.to
    if message.cc:
        mime["Cc"] = ", ".join(message.cc)
    if message.reply_to:
        mime["Reply-To"] = message.reply_to
    mime["Subject"] = message.subject
    mime.set_content(message.html, subtype="html")
    for attachment in message.attachments:
        maintype, _, subtype = attachment.content_type.partition("/")
        mime.add_attachment(
            attachment.content,
            maintype=maintype or "application",
            subtype=subtype or "octet-stream",
            filename=attachment.filename,
        )
    return mime
