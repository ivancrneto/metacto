"""Tests for date/time handling — the UTC guarantees around created_at.

Timestamps are the one place storage (naive SQLite / tz-aware Postgres) and the
HTTP contract (always an explicit UTC offset) disagree, so the normalization is
pinned down here directly.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import FeatureRequest, utcnow
from app.schemas import RequestOut


def _out(created_at: datetime) -> RequestOut:
    return RequestOut(
        id=1,
        title="t",
        description="d",
        created_at=created_at,
        vote_count=0,
        has_voted=False,
        is_author=False,
    )


def test_utcnow_is_timezone_aware_utc() -> None:
    now = utcnow()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_as_utc_stamps_naive_datetime_as_utc() -> None:
    # SQLite path: a naive value is assumed to already be UTC and stamped as such,
    # so the wall-clock reading must not shift.
    naive = datetime(2026, 1, 2, 3, 4, 5)  # noqa: DTZ001 — intentionally naive input
    out = _out(naive)
    assert out.created_at.tzinfo is not None
    assert out.created_at.utcoffset() == timedelta(0)
    assert out.created_at == naive.replace(tzinfo=UTC)


def test_as_utc_converts_aware_datetime_to_utc() -> None:
    # Postgres path: a tz-aware value in another zone is converted to UTC, keeping
    # the same instant (the branch SQLite never exercises).
    est = timezone(timedelta(hours=-5))
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=est)
    out = _out(aware)
    assert out.created_at.utcoffset() == timedelta(0)
    assert out.created_at == datetime(2026, 1, 1, 17, 0, 0, tzinfo=UTC)


def test_created_at_is_populated_on_insert(session: Session) -> None:
    before = utcnow()
    request = FeatureRequest(title="timestamped", description="d", author_id="a")
    session.add(request)
    session.commit()
    session.refresh(request)
    after = utcnow()

    assert request.created_at is not None
    # The default fired within the window around the insert (compared naively, since
    # SQLite hands the value back without a tzinfo).
    stamped = request.created_at.replace(tzinfo=UTC)
    assert before <= stamped <= after


def test_api_created_at_carries_utc_offset(client: TestClient) -> None:
    body = client.post(
        "/api/requests",
        json={"title": "Add SSO", "description": "Support SAML/OIDC login."},
    ).json()

    parsed = datetime.fromisoformat(body["created_at"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)


def test_api_created_at_ordering_is_stable(client_factory: Callable[[], TestClient]) -> None:
    # created_at drives the "new" sort; even when two inserts share a timestamp the
    # id tie-break keeps newest first.
    author = client_factory()
    author.post("/api/requests", json={"title": "first", "description": "d"})
    author.post("/api/requests", json={"title": "second", "description": "d"})

    titles = [r["title"] for r in author.get("/api/requests?sort=new").json()]
    assert titles == ["second", "first"]
