from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..deps import get_current_user
from ..models import User
from ..schemas import FeatureRequestOut, feature_request_out
from ..services import add_vote, remove_vote

router = APIRouter(prefix="/feature-requests", tags=["votes"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/{request_id}/votes",
    status_code=status.HTTP_201_CREATED,
    response_model=FeatureRequestOut,
)
async def upvote(request_id: int, user: CurrentUser, session: SessionDep) -> FeatureRequestOut:
    fr = await add_vote(session, user, request_id)
    return feature_request_out(fr, has_voted=True)


@router.delete("/{request_id}/votes", response_model=FeatureRequestOut)
async def unvote(request_id: int, user: CurrentUser, session: SessionDep) -> FeatureRequestOut:
    fr = await remove_vote(session, user, request_id)
    return feature_request_out(fr, has_voted=False)
