import secrets
from urllib.parse import urlparse

from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from .config import get_settings

COOKIE = "wg_session"


def session_id(request: Request, response: Response) -> str:
    signer = URLSafeSerializer(get_settings().signing_secret, salt="guest-session")
    value = request.cookies.get(COOKIE)
    try:
        identifier = signer.loads(value) if value else None
    except BadSignature:
        identifier = None
    if not identifier:
        identifier = secrets.token_urlsafe(24)
        response.set_cookie(
            COOKIE,
            signer.dumps(identifier),
            max_age=get_settings().game_ttl_days * 86400,
            httponly=True,
            secure=get_settings().environment == "production",
            samesite="lax",
            path="/",
        )
    return identifier


def enforce_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return
    expected = urlparse(get_settings().public_origin)
    actual = urlparse(origin)
    if (actual.scheme, actual.netloc) != (expected.scheme, expected.netloc):
        raise HTTPException(403, "Cross-origin mutation rejected")
