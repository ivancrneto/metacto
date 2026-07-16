"""Unit tests for the voting domain — the one-vote invariant and its edge cases."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import voting
from app.db.models import FeatureRequest, Vote


def _make_request(session: Session, author_id: str = "author") -> FeatureRequest:
    request = FeatureRequest(title="A good idea", description="Details.", author_id=author_id)
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def test_add_vote_counts_once_and_is_idempotent(session: Session) -> None:
    request = _make_request(session)

    first = voting.add_vote(session, request.id, "voter-1")
    assert first.vote_count == 1
    assert first.has_voted is True

    # Voting again must not create a second vote.
    second = voting.add_vote(session, request.id, "voter-1")
    assert second.vote_count == 1
    assert voting.count_votes(session, request.id) == 1


def test_distinct_voters_accumulate(session: Session) -> None:
    request = _make_request(session)
    voting.add_vote(session, request.id, "voter-1")
    result = voting.add_vote(session, request.id, "voter-2")
    assert result.vote_count == 2


def test_remove_vote_is_idempotent(session: Session) -> None:
    request = _make_request(session)
    voting.add_vote(session, request.id, "voter-1")

    removed = voting.remove_vote(session, request.id, "voter-1")
    assert removed.vote_count == 0
    assert removed.has_voted is False

    # Removing a vote that isn't there is a no-op, not an error.
    again = voting.remove_vote(session, request.id, "voter-1")
    assert again.vote_count == 0


def test_author_cannot_vote_on_own_request(session: Session) -> None:
    request = _make_request(session, author_id="me")
    with pytest.raises(voting.SelfVoteError):
        voting.add_vote(session, request.id, "me")


def test_vote_on_missing_request_raises(session: Session) -> None:
    with pytest.raises(voting.RequestNotFoundError):
        voting.add_vote(session, 4242, "voter-1")


def test_unique_constraint_is_enforced_at_the_database(session: Session) -> None:
    request = _make_request(session)
    session.add(Vote(request_id=request.id, voter_id="dup"))
    session.commit()

    # A raw duplicate insert must be rejected by the DB, not just the app layer.
    session.add(Vote(request_id=request.id, voter_id="dup"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
