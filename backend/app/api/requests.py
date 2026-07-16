"""Feature request + voting HTTP endpoints. Thin edge: validate, delegate, shape."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.api.deps import get_voter_id
from app.core import voting
from app.core.ranking import SortKey, listing_query
from app.db.models import FeatureRequest, Vote
from app.db.session import get_session

router = APIRouter(prefix="/api", tags=["requests"])

# Modern FastAPI dependency style: the callables live in Annotated metadata, not
# in mutable argument defaults.
SessionDep = Annotated[Session, Depends(get_session)]
VoterDep = Annotated[str, Depends(get_voter_id)]


def _to_out(
    request: FeatureRequest, *, vote_count: int, has_voted: bool, voter_id: str
) -> schemas.RequestOut:
    return schemas.RequestOut(
        id=request.id,
        title=request.title,
        description=request.description,
        created_at=request.created_at,
        vote_count=vote_count,
        has_voted=has_voted,
        is_author=request.author_id == voter_id,
    )


@router.post(
    "/requests",
    response_model=schemas.RequestOut,
    status_code=status.HTTP_201_CREATED,
)
def create_request(
    payload: schemas.RequestCreate,
    session: SessionDep,
    voter_id: VoterDep,
) -> schemas.RequestOut:
    request = FeatureRequest(
        title=payload.title, description=payload.description, author_id=voter_id
    )
    session.add(request)
    session.commit()
    session.refresh(request)
    return _to_out(request, vote_count=0, has_voted=False, voter_id=voter_id)


@router.get("/requests", response_model=list[schemas.RequestOut])
def list_requests(
    session: SessionDep,
    voter_id: VoterDep,
    sort: Annotated[SortKey, Query()] = SortKey.TOP,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[schemas.RequestOut]:
    rows = session.execute(listing_query(sort).limit(limit)).all()
    page_ids = [req.id for req, _ in rows]
    voted_ids = (
        set(
            session.scalars(
                select(Vote.request_id).where(
                    Vote.voter_id == voter_id, Vote.request_id.in_(page_ids)
                )
            ).all()
        )
        if page_ids
        else set()
    )
    return [
        _to_out(req, vote_count=count, has_voted=req.id in voted_ids, voter_id=voter_id)
        for req, count in rows
    ]


@router.post("/requests/{request_id}/vote", response_model=schemas.VoteOut)
def upvote(request_id: int, session: SessionDep, voter_id: VoterDep) -> schemas.VoteOut:
    try:
        result = voting.add_vote(session, request_id, voter_id)
    except voting.RequestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feature request not found") from None
    except voting.SelfVoteError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You can't upvote your own request"
        ) from None
    return schemas.VoteOut(
        request_id=result.request_id, vote_count=result.vote_count, has_voted=result.has_voted
    )


@router.delete("/requests/{request_id}/vote", response_model=schemas.VoteOut)
def remove_upvote(request_id: int, session: SessionDep, voter_id: VoterDep) -> schemas.VoteOut:
    try:
        result = voting.remove_vote(session, request_id, voter_id)
    except voting.RequestNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feature request not found") from None
    return schemas.VoteOut(
        request_id=result.request_id, vote_count=result.vote_count, has_voted=result.has_voted
    )
