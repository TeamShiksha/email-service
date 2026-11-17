"""
Errors raised by the notification layer. Routers map them to HTTP codes.
"""


class NotificationError(Exception):
    """Base class for notification errors."""


class TemplateNotFoundError(NotificationError):
    """The requested template key or legacy id is not registered."""


class InvalidRequestError(NotificationError):
    """The request cannot be delivered as given (missing data, bad address...)."""


class ProviderNotConfiguredError(NotificationError):
    """The channel/provider pair is unknown or has no credentials."""


class ProviderAuthError(NotificationError):
    """The provider rejected our credentials."""


class DeliveryError(NotificationError):
    """
    The provider failed to deliver a message.

    `retryable` marks transient failures (timeouts, 429, 5xx) that a
    provider may retry before giving up.
    """

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable
