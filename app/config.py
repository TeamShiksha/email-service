"""
For environment validation and constants
"""

import os
from typing import cast
from pydantic_settings import BaseSettings


SWAGGER_APP_DESCRIPTION = """
The EmailService is a lightweight application dedicated to sending 
emails to recipients associated with Teamshiksha projects. 

This service will be utilized by most projects, 
so all email templates should be centralized within it, 
along with maintaining updated mappings for unique template IDs.

How to use it ?
1. Add your template in `templates` folder based on your project.
2. Update the template and ID map given in `config` file.
3. Add validation in the `SendEmailRequestBody` class inside `schemas/email` file.

Code available `https://github.com/TeamShiksha/email-service`
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
    9: "teamshiksha/Welcome.html",
    10: "teamshiksha/RequestSuccess.html",
    11: "teamshiksha/RequestFail.html",
    12: "teamshiksha/Assignment.html",
    13: "swags.me/ForgotPassword.html",
    14: "swags.me/Verify.html",
    15: "teamshiksha/Interview.html",
}


class Config(BaseSettings):
    """
    Environmental variable validation class.
    """

    EMAIL_PORT: int = cast(int, os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST: str = cast(str, os.getenv("EMAIL_HOST", "smtp.gmail.com"))
    EMAIL_ADDRESS: str = cast(str, os.getenv("EMAIL_ADDRESS"))
    EMAIL_PASSWORD: str = cast(str, os.getenv("EMAIL_PASSWORD"))
    APP_SECRET: str = cast(str, os.getenv("APP_SECRET"))
    ENV: str = cast(str, os.getenv("ENV", "development"))
    ORIGINS: str = cast(str, os.getenv("ORIGINS"))
    DESCRIPTION: str = SWAGGER_APP_DESCRIPTION
    PORT: int = cast(int, os.getenv("PORT", "8000"))

    AWS_SECRET_KEY: str = cast(str, os.getenv("AWS_USER_SECRET_KEY"))
    AWS_ACCESS_KEY: str = cast(str, os.getenv("AWS_USER_ACCESS_KEY"))
    AWS_REGION: str = cast(str, os.getenv("AWS_REGION"))
    AWS_EMAIL: str = cast(str, os.getenv("AWS_EMAIL"))

config = Config()
