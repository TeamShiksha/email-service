"""
Legacy email endpoint, kept so existing callers need no changes.
"""

from fastapi import APIRouter, Depends

from app.core.auth import require_app_secret
from app.core.responses import result_response
from app.notifications.service import NotificationService
from app.schemas.legacy_email import (
    EmailProvider,
    SendEmailRequestBody,
    to_notification_request,
)

legacy_email_router = APIRouter(dependencies=[Depends(require_app_secret)])


@legacy_email_router.post("/email")
def send_email(email_details: SendEmailRequestBody):
    """
    Sends a templated email by numeric template id.

    Deprecated: prefer POST /v1/notifications. `bcc` addresses each receive
    an individual copy instead of being blind-copied on one message.

    `details` echoes the request as before; `delivery` reports what was
    sent to whom. A 207 means some recipients failed; do not retry it.
    """
    result = NotificationService().send(to_notification_request(email_details))
    if email_details.provider is None:
        # The old schema defaulted provider to SES, so the echo always named one.
        email_details = email_details.model_copy(
            update={"provider": EmailProvider(result.provider)}
        )
    return result_response(result, body=email_details, delivery=result)
