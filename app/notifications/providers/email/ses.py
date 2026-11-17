"""
Amazon SES email provider.
"""

from typing import Optional

import boto3
import botocore.exceptions

from app.notifications.errors import DeliveryError, ProviderAuthError
from app.notifications.models import Channel
from app.notifications.providers.base import Provider, with_retries
from app.notifications.providers.email.message import EmailMessage, to_mime

_AUTH_CODES = {
    "InvalidClientTokenId",
    "SignatureDoesNotMatch",
    "UnrecognizedClientException",
    "AccessDenied",
    "AccessDeniedException",
}
_RETRYABLE_CODES = {"Throttling", "ThrottlingException", "ServiceUnavailable"}


class SESEmailProvider(Provider[EmailMessage]):
    """
    Sends through SES. Messages with attachments go through SendRawEmail.
    Throttling errors are retried with backoff.
    """

    channel = Channel.EMAIL
    # Stays under SES's default production rate of 14 messages/second;
    # throttling beyond that is retried.
    max_workers = 8

    def __init__(  # pylint: disable=too-many-arguments
        self, *, name: str, access_key: str, secret_key: str, region: str, sender: str
    ):
        self.name = name
        self.sender = sender
        self.client = boto3.client(
            "ses",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def _call(self, method, **kwargs) -> dict:
        try:
            return method(**kwargs)
        except botocore.exceptions.ClientError as error:
            code = error.response.get("Error", {}).get("Code", "")
            if code in _AUTH_CODES:
                raise ProviderAuthError(f"SES authentication failed: {error}") from error
            raise DeliveryError(
                f"SES send failed: {error}", retryable=code in _RETRYABLE_CODES
            ) from error
        except botocore.exceptions.BotoCoreError as error:
            raise DeliveryError(f"SES send failed: {error}", retryable=True) from error

    def send(self, message: EmailMessage) -> Optional[str]:
        if message.attachments or message.reply_to:
            raw = to_mime(message, self.sender).as_bytes()
            response = with_retries(
                lambda: self._call(
                    self.client.send_raw_email,
                    Source=self.sender,
                    Destinations=[message.to, *message.cc],
                    RawMessage={"Data": raw},
                )
            )
        else:
            destination = {"ToAddresses": [message.to]}
            if message.cc:
                destination["CcAddresses"] = list(message.cc)
            response = with_retries(
                lambda: self._call(
                    self.client.send_email,
                    Source=self.sender,
                    Destination=destination,
                    Message={
                        "Subject": {"Data": message.subject},
                        "Body": {"Html": {"Data": message.html}},
                    },
                )
            )
        return response.get("MessageId")
