"""Unit tests for popularity ranking (top vs. new, tie-breaks)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core import voting
from app.core.ranking import SortKey, listing_query
from app.db.models import FeatureRequest


def _add(session: Session, title: str, author: str = "author") -> FeatureRequest:
    request = FeatureRequest(title=title, description="d", author_id=author)
    session.add(request)
    session.commit()
    session.refresh(request)
    return request


def _ordered(session: Session, sort: SortKey) -> list[tuple[str, int]]:
    rows = session.execute(listing_query(sort)).all()
    return [(request.title, count) for request, count in rows]


def test_top_orders_by_vote_count(session: Session) -> None:
    _add(session, "A")
    b = _add(session, "B")
    c = _add(session, "C")
    voting.add_vote(session, b.id, "v1")
    voting.add_vote(session, b.id, "v2")
    voting.add_vote(session, c.id, "v1")

    assert _ordered(session, SortKey.TOP) == [("B", 2), ("C", 1), ("A", 0)]


def test_new_orders_by_recency(session: Session) -> None:
    _add(session, "older")
    _add(session, "newer")
    assert [t for t, _ in _ordered(session, SortKey.NEW)] == ["newer", "older"]


def test_top_tie_break_prefers_older(session: Session) -> None:
    # Equal (zero) votes -> the earlier submission ranks first.
    _add(session, "older")
    _add(session, "newer")
    assert [t for t, _ in _ordered(session, SortKey.TOP)] == ["older", "newer"]
