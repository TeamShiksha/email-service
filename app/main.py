"""
Configuring the app
"""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.config import config
from app.core.exceptions import (
    http_exception_handler,
    notification_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.responses import success_response
from app.notifications.errors import NotificationError
from app.routers.legacy_email import legacy_email_router
from app.routers.notifications import notifications_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="NotificationService",
    debug=config.ENV == "development",
    version="1.0.0",
    description=config.DESCRIPTION,
    license_info={
        "name": "MIT License",
        "url": "https://github.com/TeamShiksha/email-service/blob/prod/LICENSE",
    },
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in config.ORIGINS.split(",") if o],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(NotificationError, notification_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(notifications_router, tags=["Notifications"])
app.include_router(legacy_email_router, tags=["Email (legacy)"])


@app.get("/health", tags=["Health"])
def health():
    """Liveness check."""
    return success_response(message="ok")
