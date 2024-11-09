"""
Configuring the app
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from app.config import config
from app.routers.email_router import email_router
from app.utils.exceptions import (
    custom_http_exception_handler,
    custom_general_exception_handler,
)

app = FastAPI(
    title="EmailService",
    debug=1 if config.ENV == "development" else 0,
    version="0.0.1",
    description=config.DESCRIPTION,
    license_info={
        "name": "MIT License",
        "url": "https://github.com/TeamShiksha/email-service/blob/main/LICENSE",
    },
    openapi_url="/openapi.json" if config.ENV == "development" else None,
    docs_url="/docs" if config.ENV == "development" else None,
    redoc_url="/redoc" if config.ENV == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, custom_http_exception_handler)
app.add_exception_handler(Exception, custom_general_exception_handler)

app.include_router(email_router, prefix="/api")
