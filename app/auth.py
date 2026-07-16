import base64
import binascii
import os
import secrets

from fastapi import Request
from fastapi.responses import PlainTextResponse


AUTH_EXEMPT_PATHS = {"/health"}


def _configured_credentials() -> tuple[str, str] | None:
    username = os.getenv("APP_USERNAME")
    password = os.getenv("APP_PASSWORD")
    authentication_required = os.getenv("RENDER", "").lower() == "true"

    if not username and not password and not authentication_required:
        return None
    if not username or not password:
        raise RuntimeError("Basic authentication is not configured")
    return username, password


def _decode_basic_credentials(authorization: str) -> tuple[str, str] | None:
    scheme, _, encoded = authorization.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return None

    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None

    username, separator, password = decoded.partition(":")
    if not separator:
        return None
    return username, password


async def require_basic_auth(request: Request, call_next):
    """Protect the deployed app when APP_USERNAME and APP_PASSWORD are set."""
    try:
        credentials = _configured_credentials()
    except RuntimeError:
        return PlainTextResponse(
            "Application authentication is not configured",
            status_code=503,
        )

    if credentials is None or request.url.path in AUTH_EXEMPT_PATHS:
        return await call_next(request)

    supplied = _decode_basic_credentials(request.headers.get("Authorization", ""))
    authenticated = (
        supplied is not None
        and secrets.compare_digest(
            supplied[0].encode("utf-8"),
            credentials[0].encode("utf-8"),
        )
        and secrets.compare_digest(
            supplied[1].encode("utf-8"),
            credentials[1].encode("utf-8"),
        )
    )
    if not authenticated:
        return PlainTextResponse(
            "Authentication required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Article Editor"'},
        )

    return await call_next(request)
