"""Request-scoped dependencies — anonymous voter identity via a signed cookie."""

from __future__ import annotations

import uuid

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from app.config import settings

_serializer = URLSafeSerializer(settings.secret_key, salt="voter-id")


def _unsign(raw: str) -> str | None:
    try:
        value = _serializer.loads(raw)
    except BadSignature:
        return None
    return value if isinstance(value, str) else None


def get_voter_id(request: Request, response: Response) -> str:
    """Return a stable anonymous identity for the caller.

    The id lives in a signed, httpOnly cookie. Because the frontend is served
    same-origin (Vite proxy in dev, StaticFiles in prod), SameSite=Lax suffices
    and we avoid cross-site cookie complexity. Deliberately lightweight — this is
    spoof-resistant (signed) but not authentication; swap for real auth in
    production. See README.
    """
    raw = request.cookies.get(settings.cookie_name)
    if raw and (voter_id := _unsign(raw)) is not None:
        return voter_id

    voter_id = uuid.uuid4().hex
    response.set_cookie(
        key=settings.cookie_name,
        value=_serializer.dumps(voter_id),
        max_age=settings.cookie_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return voter_id
