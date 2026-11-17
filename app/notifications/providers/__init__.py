"""
Provider registry.

Providers are built once per process, and only when their settings are
present. To add a channel (SMS, WhatsApp, push), implement `Provider` for
it and register it in `_build_registry`.
"""

from functools import lru_cache
from typing import Dict, Optional, Tuple

from app.config import config
from app.notifications.errors import InvalidRequestError, ProviderNotConfiguredError
from app.notifications.models import Channel
from app.notifications.providers.base import BatchOutcome, Provider
from app.notifications.providers.email.autosend import AutosendEmailProvider
from app.notifications.providers.email.message import EmailMessage
from app.notifications.providers.email.ses import SESEmailProvider
from app.notifications.providers.email.smtp import SMTPEmailProvider

# Provider names callers can pass, per channel.
KNOWN_PROVIDERS = {
    Channel.EMAIL: ("GMAIL", "SES", "AUTOSEND"),
    Channel.SMS: (),
    Channel.WHATSAPP: (),
    Channel.PUSH: (),
}

DEFAULT_PROVIDERS = {Channel.EMAIL: config.DEFAULT_EMAIL_PROVIDER.upper()}


@lru_cache(maxsize=None)
def _build(channel: Channel, name: str) -> Optional[Provider]:
    if channel == Channel.EMAIL:
        if name == "GMAIL" and config.EMAIL_ADDRESS and config.EMAIL_PASSWORD:
            return SMTPEmailProvider(
                name=name,
                host=config.EMAIL_HOST,
                port=config.EMAIL_PORT,
                username=config.EMAIL_ADDRESS,
                password=config.EMAIL_PASSWORD,
            )
        if name == "SES" and config.AWS_EMAIL and config.AWS_REGION:
            return SESEmailProvider(
                name=name,
                access_key=config.AWS_ACCESS_KEY,
                secret_key=config.AWS_SECRET_KEY,
                region=config.AWS_REGION,
                sender=config.AWS_EMAIL,
            )
        if name == "AUTOSEND" and config.AUTOSEND_API_KEY and config.AUTOSEND_FROM_EMAIL:
            return AutosendEmailProvider(
                name=name,
                api_key=config.AUTOSEND_API_KEY,
                from_email=config.AUTOSEND_FROM_EMAIL,
                from_name=config.AUTOSEND_FROM_NAME,
                base_url=config.AUTOSEND_BASE_URL,
                requests_per_second=config.AUTOSEND_REQUESTS_PER_SECOND,
            )
    return None


def get_provider(channel: Channel, name: Optional[str] = None) -> Provider:
    """
    Returns the named provider for a channel, or the channel default.
    """
    resolved = (name or DEFAULT_PROVIDERS.get(channel) or "").upper()
    if resolved not in KNOWN_PROVIDERS.get(channel, ()):
        raise InvalidRequestError(
            f"Unknown provider '{resolved or name}' for the {channel.value} channel."
        )
    provider = _build(channel, resolved)
    if provider is None:
        raise ProviderNotConfiguredError(
            f"Provider '{resolved}' is not configured on this deployment."
        )
    return provider


def available_providers() -> Dict[str, Tuple[str, ...]]:
    """Configured providers per channel, for the discovery endpoint."""
    return {
        channel.value: tuple(n for n in names if _build(channel, n) is not None)
        for channel, names in KNOWN_PROVIDERS.items()
    }


__all__ = [
    "BatchOutcome",
    "EmailMessage",
    "Provider",
    "available_providers",
    "get_provider",
]
