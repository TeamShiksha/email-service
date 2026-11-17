"""
Autosend email provider (https://docs.autosend.com).
"""

import base64
from typing import Dict, List, Optional, Sequence, Tuple

import requests

from app.notifications.errors import DeliveryError, ProviderAuthError
from app.notifications.models import Channel, DeliveryResult
from app.notifications.providers.base import (
    BatchOutcome,
    Provider,
    RateLimiter,
    with_retries,
)
from app.notifications.providers.email.message import EmailMessage

# Autosend's bulk endpoint accepts at most 100 recipients per request.
BULK_LIMIT = 100


class AutosendEmailProvider(Provider[EmailMessage]):  # pylint: disable=too-many-instance-attributes
    """
    Sends through Autosend.

    Messages that are identical apart from the recipient are sent through
    the bulk endpoint, where every recipient still gets their own email.
    That keeps a 500-person event update to five API calls, which matters
    with Autosend's 2 requests/second limit. Anything else goes through the
    single-send endpoint.
    """

    channel = Channel.EMAIL

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        name: str,
        api_key: str,
        from_email: str,
        from_name: str = "",
        base_url: str = "https://api.autosend.com/v1",
        requests_per_second: float = 2,
        timeout: int = 10,
    ):
        self.name = name
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.limiter = RateLimiter(requests_per_second)
        self.session = requests.Session()

    def _sender(self) -> dict:
        sender = {"email": self.from_email}
        if self.from_name:
            sender["name"] = self.from_name
        return sender

    @staticmethod
    def _addresses(emails: Sequence[str]) -> List[dict]:
        return [{"email": str(email)} for email in emails]

    def _post_once(self, path: str, payload: dict) -> dict:
        self.limiter.wait()
        try:
            response = self.session.post(
                f"{self.base_url}{path}",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
            )
        except requests.RequestException as error:
            raise DeliveryError(f"Autosend request failed: {error}", retryable=True) from error

        status = response.status_code
        if status in (401, 403):
            raise ProviderAuthError(f"Autosend authentication failed: {status} {response.text}")
        if status >= 400:
            raise DeliveryError(
                f"Autosend rejected the request: {status} {response.text}",
                retryable=status == 429 or status >= 500,
            )
        try:
            body = response.json()
        except ValueError:
            return {}
        return body.get("data", body) if isinstance(body, dict) else {}

    def _post(self, path: str, payload: dict) -> dict:
        return with_retries(lambda: self._post_once(path, payload), base_delay=1.0)

    def send(self, message: EmailMessage) -> Optional[str]:
        payload = {
            "from": self._sender(),
            "to": {"email": message.to},
            "subject": message.subject,
            "html": message.html,
        }
        if message.cc:
            payload["cc"] = self._addresses(message.cc)
        if message.reply_to:
            payload["replyTo"] = {"email": message.reply_to}
        if message.attachments:
            payload["attachments"] = [
                {
                    "fileName": a.filename,
                    "content": base64.b64encode(a.content).decode("ascii"),
                    "contentType": a.content_type,
                }
                for a in message.attachments
            ]
        return self._post("/mails/send", payload).get("emailId")

    @staticmethod
    def _bulk_key(message: EmailMessage) -> Optional[Tuple[str, str, str]]:
        """
        Messages with the same key can share one bulk request. Autosend runs
        Handlebars over bulk html, so content containing `{{` is never
        batched in case it is user text that would be mangled.
        """
        if message.attachments or "{{" in message.html or "{{" in message.subject:
            return None
        return (message.subject, message.html, message.reply_to or "")

    def _send_bulk(self, messages: List[EmailMessage], outcome: BatchOutcome) -> None:
        first = messages[0]
        payload = {
            "from": self._sender(),
            "subject": first.subject,
            "html": first.html,
            "recipients": [
                {"email": m.to, **({"cc": self._addresses(m.cc)} if m.cc else {})}
                for m in messages
            ],
        }
        if first.reply_to:
            payload["replyTo"] = {"email": first.reply_to}
        try:
            data = self._post("/mails/bulk", payload)
        except DeliveryError as error:
            outcome.results.extend(
                DeliveryResult(to=m.to, status="failed", error=str(error)) for m in messages
            )
            return

        batch_id = data.get("batchId")
        outcome.results.extend(
            DeliveryResult(to=m.to, status="sent", message_id=batch_id) for m in messages
        )
        failed = data.get("failedCount") or 0
        if failed:
            # Autosend reports a count, not which recipients (typically
            # suppressed addresses), so surface it rather than guess.
            outcome.warnings.append(
                f"Autosend batch {batch_id} accepted {data.get('successCount')} of "
                f"{len(messages)} recipients; {failed} were rejected (likely suppressed)."
            )

    def send_batch(self, messages: Sequence[EmailMessage]) -> BatchOutcome:
        outcome = BatchOutcome(results=[])
        singles: List[EmailMessage] = []
        groups: Dict[Tuple[str, str, str], List[EmailMessage]] = {}
        for message in messages:
            key = self._bulk_key(message)
            if key is None:
                singles.append(message)
            else:
                groups.setdefault(key, []).append(message)

        for group in groups.values():
            if len(group) == 1:
                singles.extend(group)
                continue
            for start in range(0, len(group), BULK_LIMIT):
                self._send_bulk(group[start : start + BULK_LIMIT], outcome)

        if singles:
            single_outcome = super().send_batch(singles)
            outcome.results.extend(single_outcome.results)
        return outcome
