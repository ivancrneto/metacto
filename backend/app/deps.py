"""Request identity.

Auth is intentionally a thin seam: the client sends an ``X-User`` header and we
resolve (or lazily create) that user. Everything downstream depends only on
``get_current_user`` / ``get_optional_user``, so swapping in real OAuth/session
auth later is a one-file change. See ADR-0002.
"""

import re
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import User

USERNAME_RE = re.compile(r"^[a-z0-9_-]{1,50}$")


def _normalize(x_user: str | None) -> str | None:
    if x_user is None:
        return None
    normalized = x_user.strip().lower()
    return normalized or None


def _validate(username: str) -> None:
    if not USERNAME_RE.match(username):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid username; use 1-50 characters from [a-z0-9_-].",
        )


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_user: Annotated[str | None, Header()] = None,
) -> User:
    """Require a valid identity, creating the user row on first sight."""
    username = _normalize(x_user)
    if username is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing or empty X-User header.")
    _validate(username)

    found: User | None = await session.scalar(select(User).where(User.username == username))
    if found is not None:
        return found

    user = User(username=username)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        # Concurrent first-request for the same username — reuse the winner.
        await session.rollback()
        winner: User | None = await session.scalar(select(User).where(User.username == username))
        if winner is None:  # pragma: no cover - defensive
            raise
        return winner
    await session.refresh(user)
    return user


async def get_optional_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_user: Annotated[str | None, Header()] = None,
) -> User | None:
    """Resolve the viewer for read endpoints without creating a row."""
    username = _normalize(x_user)
    if username is None or not USERNAME_RE.match(username):
        return None
    user: User | None = await session.scalar(select(User).where(User.username == username))
    return user
