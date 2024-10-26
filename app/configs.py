"""
For environment validation and constants
"""

import os
from typing import cast
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """
    Environmental variable validation class.
    """

    PORT: int = cast(int, os.getenv("PORT", 8000))
    EMAIL_PORT: int = cast(int, os.getenv("EMAIL_PORT", 587))
    EMAIL_HOST: str = cast(str, os.getenv("EMAIL_HOST", "smtp.gmail.com"))
    EMAIL_ADDRESS: str = cast(str, os.getenv("EMAIL_ADDRESS"))
    EMAIL_PASSWORD: str = cast(str, os.getenv("EMAIL_PASSWORD"))
    APP_SECRET: str = cast(str, os.getenv("APP_SECRET"))
    ENV: str = cast(str, os.getenv("ENV", "development"))


config = Config()

ORIGINS = ["*"]

DESCRIPTION = """
The EmailService is a lightweight application dedicated to sending 
emails to recipients associated with Teamshiksha projects. 

This service will be utilized by most projects, 
so all email templates should be centralized within it, 
along with maintaining updated mappings for unique template IDs.

How to use it ?
1. Add your template in `templates` folder.
2. Update the template and ID map given in `configs` file.
3. Add validation in the `SendEmailRequestBody` class inside `schemas` file.

Code available `https://github.com/TeamShiksha/email-service`
"""

template_hash_map = {"1": "template link", "2": "template link"}
