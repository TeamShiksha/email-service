"""
Authentication for callers (other TeamShiksha services).
"""

import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import config


def require_app_secret(authorization: Optional[str] = Header(default=None)) -> None:
    """
    Checks the shared APP_SECRET. Accepts the raw secret, which existing
    callers send, or `Bearer <secret>`.
    """
    secret = config.APP_SECRET
    token = (authorization or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not secret or not token or not hmac.compare_digest(token.encode(), secret.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
