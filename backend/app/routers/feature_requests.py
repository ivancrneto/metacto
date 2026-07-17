from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user, get_optional_user
from ..models import FeatureRequest, User, Vote
from ..ranking import apply_sort
from ..schemas import (
    FeatureRequestCreate,
    FeatureRequestOut,
    Page,
    SortMode,
    feature_request_out,
)

router = APIRouter(prefix="/feature-requests", tags=["feature-requests"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=FeatureRequestOut)
async def create_feature_request(
    payload: FeatureRequestCreate,
    user: Annotated[User, Depends(get_current_user)],
    session: SessionDep,
) -> FeatureRequestOut:
    fr = FeatureRequest(
        title=payload.title,
        description=payload.description,
        author_id=user.id,
        vote_count=0,
    )
    session.add(fr)
    await session.commit()
    await session.refresh(fr)
    return feature_request_out(fr, has_voted=False)


@router.get("", response_model=Page)
async def list_feature_requests(
    session: SessionDep,
    viewer: Annotated[User | None, Depends(get_optional_user)],
    sort: SortMode = SortMode.top,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page:
    total = await session.scalar(select(func.count()).select_from(FeatureRequest)) or 0

    stmt = apply_sort(select(FeatureRequest), sort).limit(page_size).offset((page - 1) * page_size)
    rows = list((await session.scalars(stmt)).all())

    voted_ids: set[int] = set()
    if viewer is not None and rows:
        ids = [r.id for r in rows]
        voted_ids = set(
            (
                await session.scalars(
                    select(Vote.request_id).where(
                        Vote.user_id == viewer.id, Vote.request_id.in_(ids)
                    )
                )
            ).all()
        )

    items = [feature_request_out(r, has_voted=r.id in voted_ids) for r in rows]
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=page * page_size < total,
    )


@router.get("/{request_id}", response_model=FeatureRequestOut)
async def get_feature_request(
    request_id: int,
    session: SessionDep,
    viewer: Annotated[User | None, Depends(get_optional_user)],
) -> FeatureRequestOut:
    fr = await session.scalar(select(FeatureRequest).where(FeatureRequest.id == request_id))
    if fr is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Feature request not found.")

    has_voted = False
    if viewer is not None:
        voted = await session.scalar(
            select(func.count())
            .select_from(Vote)
            .where(Vote.user_id == viewer.id, Vote.request_id == request_id)
        )
        has_voted = bool(voted)

    return feature_request_out(fr, has_voted=has_voted)
