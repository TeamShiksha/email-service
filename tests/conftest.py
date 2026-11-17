"""
Shared fixtures. Settings are set before the app is imported.
"""

import os

os.environ.setdefault("APP_SECRET", "test-secret")
os.environ.setdefault("DEFAULT_EMAIL_PROVIDER", "SES")
os.environ.setdefault("EMAIL_ADDRESS", "sender@teamshiksha.org")

from typing import List, Optional  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.notifications import service as service_module  # noqa: E402
from app.notifications.models import Channel  # noqa: E402
from app.notifications.providers.base import Provider  # noqa: E402
from app.notifications.providers.email.message import EmailMessage  # noqa: E402

AUTH = {"Authorization": "test-secret"}


class FakeEmailProvider(Provider[EmailMessage]):
    """Records messages instead of sending them."""

    channel = Channel.EMAIL

    def __init__(self, name: str = "SES", fail_for: Optional[set] = None):
        self.name = name
        self.sent: List[EmailMessage] = []
        self.fail_for = fail_for or set()

    def send(self, message: EmailMessage) -> Optional[str]:
        if message.to in self.fail_for:
            raise RuntimeError("mailbox unavailable")
        self.sent.append(message)
        return f"id-{len(self.sent)}"


@pytest.fixture
def provider(monkeypatch):
    """Replaces provider lookup with a fake; records the requested name."""
    fake = FakeEmailProvider()
    requested = {}

    def get_provider(channel, name=None):
        requested["channel"] = channel
        requested["name"] = name
        return fake

    monkeypatch.setattr(service_module, "get_provider", get_provider)
    fake.requested = requested
    return fake


@pytest.fixture
def client():
    """Test client that does not re-raise server errors."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Retries and rate limiting should not slow tests down."""
    import app.notifications.providers.base as base

    monkeypatch.setattr(base.time, "sleep", lambda _s: None)
