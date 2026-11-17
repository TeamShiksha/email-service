"""
Turns a NotificationRequest into one message per recipient and delivers
them through the chosen provider.
"""

import logging
from typing import Any, Callable, Dict, List

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.config import config
from app.notifications import templates
from app.notifications.errors import InvalidRequestError
from app.notifications.models import (
    Channel,
    NotificationRequest,
    NotificationResult,
    Recipient,
)
from app.notifications.providers import EmailMessage, get_provider
from app.notifications.templates import TemplateDefinition

logger = logging.getLogger(__name__)

_email_adapter = TypeAdapter(EmailStr)


def _dedupe(recipients: List[Recipient]) -> List[Recipient]:
    """Drops repeat recipients so nobody gets the same message twice."""
    seen = set()
    unique = []
    for recipient in recipients:
        key = recipient.to.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(recipient)
    return unique


def _valid_email(address: str) -> str:
    try:
        return str(_email_adapter.validate_python(address.strip()))
    except ValidationError as error:
        raise InvalidRequestError(f"'{address}' is not a valid email address.") from error


def _build_email_messages(
    request: NotificationRequest,
    definition: TemplateDefinition,
    recipients: List[Recipient],
) -> List[EmailMessage]:
    subject = request.subject or definition.default_subject
    if not subject:
        raise InvalidRequestError("A subject is required for email.")

    # Recipients without their own data share one rendering.
    shared: Dict[str, Any] = {}
    messages = []
    for recipient in recipients:
        data = {**request.data, **recipient.data}
        templates.check_required(definition, data)
        if recipient.data or "html" not in shared:
            rendered = {
                "html": templates.render(definition, Channel.EMAIL, data),
                "attachments": definition.attachments(data) if definition.attachments else [],
            }
            if not recipient.data:
                shared = rendered
        else:
            rendered = shared
        messages.append(
            EmailMessage(
                to=_valid_email(recipient.to),
                cc=[str(c) for c in recipient.cc],
                subject=subject,
                html=rendered["html"],
                reply_to=str(request.reply_to) if request.reply_to else None,
                attachments=list(rendered["attachments"]),
            )
        )
    return messages


# One builder per channel. Adding a channel means adding its builder here
# and its providers in `app.notifications.providers`.
_BUILDERS: Dict[Channel, Callable[..., list]] = {
    Channel.EMAIL: _build_email_messages,
}


class NotificationService:
    """Validates, renders and delivers notifications."""

    def send(self, request: NotificationRequest) -> NotificationResult:
        """
        Sends the notification to every recipient individually.

        Everything is validated and rendered before the first message goes
        out, so a bad request never results in a partial send.
        """
        definition = templates.get_template(request.template)
        if request.channel not in definition.channels:
            raise InvalidRequestError(
                f"Template '{definition.key}' is not available on {request.channel.value}."
            )
        builder = _BUILDERS.get(request.channel)
        if builder is None:
            raise InvalidRequestError(f"The {request.channel.value} channel is not supported yet.")

        recipients = _dedupe(request.recipients)
        limit = config.MAX_RECIPIENTS_PER_REQUEST
        if len(recipients) > limit:
            raise InvalidRequestError(
                f"{len(recipients)} recipients exceeds the limit of {limit} per request; "
                "split the audience across requests."
            )

        provider = get_provider(request.channel, request.provider)
        messages = builder(request, definition, recipients)
        outcome = provider.send_batch(messages)

        sent = sum(1 for r in outcome.results if r.status == "sent")
        result = NotificationResult(
            template=definition.key,
            channel=request.channel,
            provider=provider.name,
            total=len(outcome.results),
            sent=sent,
            failed=len(outcome.results) - sent,
            results=outcome.results,
            warnings=outcome.warnings,
        )
        logger.info(
            "notification template=%s channel=%s provider=%s sent=%d failed=%d",
            result.template,
            result.channel.value,
            result.provider,
            result.sent,
            result.failed,
        )
        return result
