"""Vote business rules.

Enforces "one vote per user per request" (DB UNIQUE constraint) and "no
self-votes", keeping ``feature_requests.vote_count`` in lockstep with the
``votes`` table inside a single transaction via an atomic
``SET vote_count = vote_count ± 1``. All SQL is delegated to repository.py.
See ADR-0003.
"""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from . import repository
from .models import FeatureRequest, User


async def _require_request(session: AsyncSession, request_id: int) -> FeatureRequest:
    fr = await repository.get_request(session, request_id)
    if fr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feature request not found.")
    return fr


async def add_vote(session: AsyncSession, user: User, request_id: int) -> FeatureRequest:
    fr = await _require_request(session, request_id)
    if fr.author_id == user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You cannot vote on your own feature request.",
        )

    try:
        await repository.insert_vote(session, user.id, request_id)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="You have already voted for this request.",
        ) from None

    await repository.change_vote_count(session, request_id, +1)
    await session.commit()
    await session.refresh(fr)  # pull the DB-computed vote_count back into the ORM
    return fr


async def remove_vote(session: AsyncSession, user: User, request_id: int) -> FeatureRequest:
    fr = await _require_request(session, request_id)

    vote = await repository.get_vote(session, user.id, request_id)
    if vote is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="You have not voted for this request.",
        )

    await repository.delete_vote(session, vote)
    await repository.change_vote_count(session, request_id, -1)
    await session.commit()
    await session.refresh(fr)
    return fr
