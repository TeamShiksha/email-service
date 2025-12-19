"""
For environment validation and constants
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


SWAGGER_APP_DESCRIPTION = """
The EmailService is a lightweight application dedicated to sending 
emails to recipients associated with Teamshiksha projects. 

This service will be utilized by most projects, 
so all email templates should be centralized within it.
"""

TEMPLATE_HASH_MAP = {
    1: "openlogo/ForgotPassword.html",
    2: "openlogo/Verify.html",
    3: "openlogo/Respond.html",
    4: "rsvp/Verify.html",
    5: "rsvp/ticket.html",
    6: "rsvp/update.html",
    7: "rsvp/invite.html",
    8: "teamshiksha/ForgotPassword.html",
}


class Config(BaseSettings):
    # App
    ENV: str = "development"
    DESCRIPTION: str = SWAGGER_APP_DESCRIPTION
    PORT: int = 8000

    # Email
    EMAIL_ADDRESS: str
    EMAIL_PASSWORD: str
    EMAIL_PORT: int = 587
    EMAIL_HOST: str = "smtp.gmail.com"

    # Security
    APP_SECRET: str
    ORIGINS: str

    # AWS
    AWS_ACCESS_KEY: str
    AWS_SECRET_KEY: str
    AWS_REGION: str
    AWS_EMAIL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


config = Config()
