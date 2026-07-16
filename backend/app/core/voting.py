"""Voting rules — the one genuinely tricky piece of domain logic.

Kept free of any web-framework imports so it can be unit-tested directly against
a session. Integrity (one vote per user per request) is ultimately guaranteed by
a UNIQUE constraint in the database; this layer enforces the product rules
(no self-votes, idempotent add/remove) and reconciles the concurrent-vote race.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import FeatureRequest, Vote


class VotingError(Exception):
    """Base class for voting domain errors."""


class RequestNotFoundError(VotingError):
    """Voting target does not exist."""


class SelfVoteError(VotingError):
    """A user tried to upvote their own request."""


@dataclass(frozen=True)
class VoteResult:
    request_id: int
    vote_count: int
    has_voted: bool


def count_votes(session: Session, request_id: int) -> int:
    total = session.scalar(
        select(func.count()).select_from(Vote).where(Vote.request_id == request_id)
    )
    return int(total or 0)


def _require_request(session: Session, request_id: int) -> FeatureRequest:
    request = session.get(FeatureRequest, request_id)
    if request is None:
        raise RequestNotFoundError(request_id)
    return request


def add_vote(session: Session, request_id: int, voter_id: str) -> VoteResult:
    """Register an upvote. Idempotent: voting again is a no-op, not a second vote."""
    request = _require_request(session, request_id)
    if request.author_id == voter_id:
        raise SelfVoteError(request_id)

    already_voted = session.scalar(
        select(Vote).where(Vote.request_id == request_id, Vote.voter_id == voter_id)
    )
    if already_voted is None:
        session.add(Vote(request_id=request_id, voter_id=voter_id))
        try:
            session.commit()
        except IntegrityError:
            # A concurrent request inserted the same vote first; the UNIQUE
            # constraint held the line, so the end state is still "voted".
            session.rollback()

    return VoteResult(request_id, count_votes(session, request_id), has_voted=True)


def remove_vote(session: Session, request_id: int, voter_id: str) -> VoteResult:
    """Retract an upvote. Idempotent: removing a vote that isn't there is a no-op."""
    _require_request(session, request_id)
    existing = session.scalar(
        select(Vote).where(Vote.request_id == request_id, Vote.voter_id == voter_id)
    )
    if existing is not None:
        session.delete(existing)
        session.commit()

    return VoteResult(request_id, count_votes(session, request_id), has_voted=False)
