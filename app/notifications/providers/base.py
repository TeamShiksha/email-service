"""
Provider contract shared by every channel.
"""

import logging
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Generic, List, Optional, Sequence, TypeVar

from app.notifications.errors import DeliveryError, ProviderAuthError
from app.notifications.models import Channel, DeliveryResult

logger = logging.getLogger(__name__)

M = TypeVar("M")
R = TypeVar("R")


@dataclass
class BatchOutcome:
    """Per-message results plus any provider-level warnings."""

    results: List[DeliveryResult]
    warnings: List[str] = field(default_factory=list)


class Provider(ABC, Generic[M]):
    """
    Sends messages of type M on one channel.

    Implement `send` for a single message. Override `send_batch` when the
    provider can do better than one call per message (reuse a connection,
    a bulk endpoint...). Each message always has exactly one recipient, so
    recipients never see each other.
    """

    channel: Channel
    name: str
    # Messages sent in parallel by the default send_batch. Callers time out
    # after 5-10s, so large audiences must not go out strictly one by one.
    max_workers: int = 1

    @abstractmethod
    def send(self, message: M) -> Optional[str]:
        """Sends one message and returns the provider's message id."""

    @staticmethod
    def recipient_of(message: M) -> str:
        """The address a message is going to, for reporting."""
        return getattr(message, "to")

    def send_batch(self, messages: Sequence[M]) -> BatchOutcome:
        """
        Sends messages one by one. A failure only affects its own message,
        except an authentication failure, which would fail every message
        and so stops the batch.
        """
        if self.max_workers > 1 and len(messages) > 1:
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(messages))) as pool:
                results = list(pool.map(self._deliver, messages))
        else:
            results = [self._deliver(message) for message in messages]
        return BatchOutcome(results=results)

    def _deliver(self, message: M) -> DeliveryResult:
        to = self.recipient_of(message)
        try:
            message_id = self.send(message)
            return DeliveryResult(to=to, status="sent", message_id=message_id)
        except ProviderAuthError:
            raise
        except Exception as error:  # pylint: disable=broad-except
            logger.warning("%s failed for %s: %s", self.name, to, error)
            return DeliveryResult(to=to, status="failed", error=str(error))


def with_retries(
    func: Callable[[], R], attempts: int = 3, base_delay: float = 0.5
) -> R:
    """
    Calls `func`, retrying DeliveryErrors marked retryable with exponential
    backoff. Other errors propagate immediately.
    """
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except DeliveryError as error:
            if not error.retryable or attempt == attempts:
                raise
            time.sleep(base_delay * 2 ** (attempt - 1))
    raise AssertionError("unreachable")


class RateLimiter:
    """
    Spaces calls at least 1/rate seconds apart within this process.
    Serverless instances do not share it, so providers also retry on 429.
    """

    def __init__(self, per_second: float):
        self.interval = 1.0 / per_second if per_second > 0 else 0.0
        self._next = 0.0

    def wait(self) -> None:
        """Blocks until the next call is allowed."""
        now = time.monotonic()
        if now < self._next:
            time.sleep(self._next - now)
            now = self._next
        self._next = now + self.interval
