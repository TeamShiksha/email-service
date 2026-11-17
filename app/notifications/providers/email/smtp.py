"""
SMTP email provider (used for Gmail).
"""

import smtplib
from typing import Optional, Sequence

from app.notifications.errors import DeliveryError, ProviderAuthError
from app.notifications.models import Channel, DeliveryResult
from app.notifications.providers.base import BatchOutcome, Provider
from app.notifications.providers.email.message import EmailMessage, to_mime


class SMTPEmailProvider(Provider[EmailMessage]):
    """
    Sends over SMTP with STARTTLS. A batch reuses one connection.

    Gmail accounts have low daily sending limits; use SES or Autosend for
    anything beyond a handful of messages.
    """

    channel = Channel.EMAIL

    def __init__(  # pylint: disable=too-many-arguments
        self, *, name: str, host: str, port: int, username: str, password: str
    ):
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def _connect(self) -> smtplib.SMTP:
        try:
            server = smtplib.SMTP(self.host, self.port, timeout=15)
            server.starttls()
            server.login(self.username, self.password)
            return server
        except smtplib.SMTPAuthenticationError as error:
            raise ProviderAuthError(f"SMTP authentication failed: {error}") from error
        except (smtplib.SMTPException, OSError) as error:
            raise DeliveryError(f"SMTP connection failed: {error}", retryable=True) from error

    def _send_on(self, server: smtplib.SMTP, message: EmailMessage) -> None:
        try:
            server.send_message(to_mime(message, self.username))
        except smtplib.SMTPSenderRefused as error:
            raise DeliveryError(f"Sender address refused: {error}") from error
        except smtplib.SMTPException as error:
            raise DeliveryError(f"SMTP send failed: {error}") from error

    def send(self, message: EmailMessage) -> Optional[str]:
        """Sends one message. SMTP returns no message id."""
        with self._connect() as server:
            self._send_on(server, message)

    def send_batch(self, messages: Sequence[EmailMessage]) -> BatchOutcome:
        results = []
        with self._connect() as server:
            for message in messages:
                try:
                    self._send_on(server, message)
                    results.append(DeliveryResult(to=message.to, status="sent"))
                except DeliveryError as error:
                    results.append(
                        DeliveryResult(to=message.to, status="failed", error=str(error))
                    )
        return BatchOutcome(results=results)
