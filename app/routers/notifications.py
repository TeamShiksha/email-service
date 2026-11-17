"""
Channel-agnostic notification API.
"""

from fastapi import APIRouter, Depends

from app.core.auth import require_app_secret
from app.core.responses import result_response, success_response
from app.notifications import templates
from app.notifications.models import NotificationRequest
from app.notifications.providers import available_providers
from app.notifications.service import NotificationService

notifications_router = APIRouter(prefix="/v1", dependencies=[Depends(require_app_secret)])


@notifications_router.post("/notifications")
def send_notification(request: NotificationRequest):
    """
    Sends a template to each recipient as an individual message.

    Status codes: 200 all sent, 207 some failed (see `details.results`),
    404 unknown template, 422 invalid request, 502 none sent, 503 provider
    not configured. Do not retry a 207; the successful recipients already
    received it.
    """
    return result_response(NotificationService().send(request))


@notifications_router.get("/templates")
def list_templates():
    """Registered templates, the data they need, and configured providers."""
    return success_response(
        message="Success",
        body={
            "templates": [
                {
                    "key": d.key,
                    "channels": [c.value for c in d.channels],
                    "required": sorted(d.required),
                    "legacy_id": d.legacy_id,
                }
                for d in templates.TEMPLATES.values()
            ],
            "providers": available_providers(),
        },
    )
