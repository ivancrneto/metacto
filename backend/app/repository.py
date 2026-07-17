"""Data-access layer.

All feature-request / vote SQL lives here, so routers and services depend on
*intent* (create / list / get_vote / …) rather than on query construction. This
module holds no business rules and no HTTP concerns — those live in the routers
and in services.py.
"""

from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import FeatureRequest, Vote
from .ranking import apply_sort
from .schemas import SortMode

# --- feature requests -------------------------------------------------------


async def add_request(session: AsyncSession, fr: FeatureRequest) -> FeatureRequest:
    session.add(fr)
    await session.commit()
    await session.refresh(fr)
    return fr


async def get_request(session: AsyncSession, request_id: int) -> FeatureRequest | None:
    fr: FeatureRequest | None = await session.scalar(
        select(FeatureRequest).where(FeatureRequest.id == request_id)
    )
    return fr


async def count_requests(session: AsyncSession) -> int:
    total = await session.scalar(select(func.count()).select_from(FeatureRequest))
    return total or 0


async def list_requests(
    session: AsyncSession, sort: SortMode, limit: int, offset: int
) -> Sequence[FeatureRequest]:
    stmt = apply_sort(select(FeatureRequest), sort).limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())


# --- votes ------------------------------------------------------------------


async def get_vote(session: AsyncSession, user_id: int, request_id: int) -> Vote | None:
    vote: Vote | None = await session.scalar(
        select(Vote).where(Vote.user_id == user_id, Vote.request_id == request_id)
    )
    return vote


async def insert_vote(session: AsyncSession, user_id: int, request_id: int) -> None:
    """Insert a vote and flush so a duplicate surfaces as IntegrityError now."""
    session.add(Vote(user_id=user_id, request_id=request_id))
    await session.flush()


async def delete_vote(session: AsyncSession, vote: Vote) -> None:
    await session.delete(vote)


async def change_vote_count(session: AsyncSession, request_id: int, delta: int) -> None:
    """Atomic DB-side tally update: SET vote_count = vote_count + delta."""
    await session.execute(
        update(FeatureRequest)
        .where(FeatureRequest.id == request_id)
        .values(vote_count=FeatureRequest.vote_count + delta)
    )


async def voted_request_ids(
    session: AsyncSession, user_id: int, request_ids: Sequence[int]
) -> set[int]:
    """Which of ``request_ids`` the user has voted on (single batched query)."""
    if not request_ids:
        return set()
    rows = await session.scalars(
        select(Vote.request_id).where(Vote.user_id == user_id, Vote.request_id.in_(request_ids))
    )
    return set(rows.all())


async def has_voted(session: AsyncSession, user_id: int, request_id: int) -> bool:
    count = await session.scalar(
        select(func.count())
        .select_from(Vote)
        .where(Vote.user_id == user_id, Vote.request_id == request_id)
    )
    return bool(count)
