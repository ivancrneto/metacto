"""Vote mutations.

Both operations keep ``feature_requests.vote_count`` in lockstep with the
``votes`` table inside a single transaction, using an atomic
``SET vote_count = vote_count +/- 1`` so the tally never races. See ADR-0003.
"""

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import FeatureRequest, User, Vote


async def _get_request(session: AsyncSession, request_id: int) -> FeatureRequest:
    fr = await session.scalar(select(FeatureRequest).where(FeatureRequest.id == request_id))
    if fr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feature request not found.")
    return fr


async def add_vote(session: AsyncSession, user: User, request_id: int) -> FeatureRequest:
    fr = await _get_request(session, request_id)
    if fr.author_id == user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="You cannot vote on your own feature request.",
        )

    session.add(Vote(user_id=user.id, request_id=request_id))
    try:
        await session.flush()  # surface the UNIQUE violation now
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="You have already voted for this request.",
        ) from None

    await session.execute(
        update(FeatureRequest)
        .where(FeatureRequest.id == request_id)
        .values(vote_count=FeatureRequest.vote_count + 1)
    )
    await session.commit()
    await session.refresh(fr)  # pull the DB-computed vote_count back into the ORM
    return fr


async def remove_vote(session: AsyncSession, user: User, request_id: int) -> FeatureRequest:
    fr = await _get_request(session, request_id)

    vote = await session.scalar(
        select(Vote).where(Vote.user_id == user.id, Vote.request_id == request_id)
    )
    if vote is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="You have not voted for this request.",
        )

    await session.delete(vote)
    await session.execute(
        update(FeatureRequest)
        .where(FeatureRequest.id == request_id)
        .values(vote_count=FeatureRequest.vote_count - 1)
    )
    await session.commit()
    await session.refresh(fr)
    return fr
