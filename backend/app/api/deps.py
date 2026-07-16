"""Anonymous voter identity.

Assigned by middleware and read via a dependency. Doing the assignment in
middleware (rather than only in a dependency) means the identity cookie is
attached to *every* response — including error responses, where a dependency's
injected Response object would otherwise be discarded.
"""

from __future__ import annotations

import uuid

from fastapi import Request, Response
from itsdangerous import BadSignature, URLSafeSerializer
from starlette.middleware.base import RequestResponseEndpoint

from app.config import settings

_serializer = URLSafeSerializer(settings.secret_key, salt="voter-id")


def _unsign(raw: str) -> str | None:
    try:
        value = _serializer.loads(raw)
    except BadSignature:
        return None
    return value if isinstance(value, str) else None


async def identity_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Ensure every request carries a stable, signed, http-only identity cookie.

    Same-origin serving (Vite proxy in dev, StaticFiles in prod) means
    SameSite=Lax is sufficient and cross-site cookie complexity is avoided. This
    is spoof-resistant (signed) but not authentication — swap for real auth in
    production. See README.
    """
    raw = request.cookies.get(settings.cookie_name)
    voter_id = _unsign(raw) if raw else None
    issue_cookie = voter_id is None
    if voter_id is None:
        voter_id = uuid.uuid4().hex
    request.state.voter_id = voter_id

    response = await call_next(request)

    if issue_cookie:
        response.set_cookie(
            key=settings.cookie_name,
            value=_serializer.dumps(voter_id),
            max_age=settings.cookie_max_age,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            path="/",
        )
    return response


def get_voter_id(request: Request) -> str:
    """Return the identity assigned to this request by identity_middleware."""
    voter_id: str = request.state.voter_id
    return voter_id
