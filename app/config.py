"""
Environment validation and app-wide settings.

Template definitions live in `app/notifications/templates.py`.
"""

import os
from typing import Optional, cast
from pydantic_settings import BaseSettings, SettingsConfigDict


SWAGGER_APP_DESCRIPTION = """
The NotificationService is a lightweight, shared service that delivers
notifications for every TeamShiksha project. Email is supported today;
the API is channel-agnostic so SMS, WhatsApp and push can be added as
providers without changing callers.

**New integrations** should call `POST /v1/notifications` with a template
key such as `rsvp.update`. Every recipient gets their own message, so
large audiences never share a single BCC'd email.

**Existing integrations** that call `POST /email` with a numeric template
id keep working unchanged. Their `bcc` lists are delivered as individual
messages behind the scenes.

How to add a template:
1. Add the file under `templates/<project>/`.
2. Register it in `app/notifications/templates.py` with its required variables.

See `DEVELOPMENT.md` and `docs/notification-service.md` for details.

Code available `https://github.com/TeamShiksha/email-service`
"""


class Config(BaseSettings):
    """
    Environmental variable validation class.
    """

    # Read .env here rather than relying on run.py's load_dotenv(), which runs
    # after this class is instantiated at import time. Real environment
    # variables still take precedence, so hosted deployments are unaffected.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_SECRET: str  # required: shared secret callers send in Authorization
    ENV: str = cast(str, os.getenv("ENV", "development"))
    ORIGINS: str = cast(str, os.getenv("ORIGINS", ""))
    DESCRIPTION: str = SWAGGER_APP_DESCRIPTION
    PORT: int = cast(int, os.getenv("PORT", "8000"))

    # Provider used when a request does not name one. SES matches the
    # behaviour existing callers of POST /email rely on.
    DEFAULT_EMAIL_PROVIDER: str = cast(str, os.getenv("DEFAULT_EMAIL_PROVIDER", "SES"))
    # Upper bound on recipients in one request. Each recipient is a separate
    # message, so this keeps a single request inside serverless time limits.
    MAX_RECIPIENTS_PER_REQUEST: int = cast(
        int, os.getenv("MAX_RECIPIENTS_PER_REQUEST", "500")
    )

    # Provider settings are optional: a provider is available only when
    # its settings are present.

    # Gmail / generic SMTP
    EMAIL_PORT: int = cast(int, os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST: str = cast(str, os.getenv("EMAIL_HOST", "smtp.gmail.com"))
    EMAIL_ADDRESS: Optional[str] = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")

    # Amazon SES
    AWS_SECRET_KEY: Optional[str] = os.getenv("AWS_USER_SECRET_KEY")
    AWS_ACCESS_KEY: Optional[str] = os.getenv("AWS_USER_ACCESS_KEY")
    AWS_REGION: Optional[str] = os.getenv("AWS_REGION")
    AWS_EMAIL: Optional[str] = os.getenv("AWS_EMAIL")

    # Autosend
    AUTOSEND_API_KEY: str = cast(str, os.getenv("AUTOSEND_API_KEY", ""))
    AUTOSEND_FROM_EMAIL: str = cast(str, os.getenv("AUTOSEND_FROM_EMAIL", ""))
    AUTOSEND_FROM_NAME: str = cast(str, os.getenv("AUTOSEND_FROM_NAME", ""))
    AUTOSEND_BASE_URL: str = cast(
        str, os.getenv("AUTOSEND_BASE_URL", "https://api.autosend.com/v1")
    )
    # Autosend's documented default is 2 requests/second per API key.
    AUTOSEND_REQUESTS_PER_SECOND: float = cast(
        float, os.getenv("AUTOSEND_REQUESTS_PER_SECOND", "2")
    )


config = Config()
