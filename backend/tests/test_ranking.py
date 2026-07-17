"""Ranking invariants across the three sort modes + pagination."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FeatureRequest, User

RequestFactory = Callable[..., Awaitable[dict[str, Any]]]


async def _seed_old_popular_and_new_small(db: AsyncSession) -> None:
    """Plant two requests where votes and recency disagree.

    "Old popular": many votes but 100h old.
    "New small":   few votes but a minute old.
    """
    author = User(username="author")
    db.add(author)
    await db.flush()

    now = datetime.now(UTC)
    db.add_all(
        [
            FeatureRequest(
                title="Old popular",
                description="x",
                author_id=author.id,
                vote_count=10,
                created_at=now - timedelta(hours=100),
            ),
            FeatureRequest(
                title="New small",
                description="x",
                author_id=author.id,
                vote_count=3,
                created_at=now - timedelta(minutes=1),
            ),
        ]
    )
    await db.commit()


async def test_sort_top_orders_by_votes(client: AsyncClient, db: AsyncSession) -> None:
    await _seed_old_popular_and_new_small(db)
    items = (await client.get("/feature-requests?sort=top")).json()["items"]
    assert [i["title"] for i in items] == ["Old popular", "New small"]


async def test_sort_new_orders_by_recency(client: AsyncClient, db: AsyncSession) -> None:
    await _seed_old_popular_and_new_small(db)
    items = (await client.get("/feature-requests?sort=new")).json()["items"]
    assert [i["title"] for i in items] == ["New small", "Old popular"]


async def test_sort_trending_weights_recency(client: AsyncClient, db: AsyncSession) -> None:
    await _seed_old_popular_and_new_small(db)
    items = (await client.get("/feature-requests?sort=trending")).json()["items"]
    # Recency decay lifts the newer, lower-vote request above the stale leader.
    assert [i["title"] for i in items] == ["New small", "Old popular"]


async def test_trending_handles_future_created_at(client: AsyncClient, db: AsyncSession) -> None:
    # A future-dated row makes the trending base negative; without a clamp,
    # Postgres errors on power(negative, fractional) and 500s the whole list.
    author = User(username="author")
    db.add(author)
    await db.flush()
    db.add(
        FeatureRequest(
            title="Future dated",
            description="x",
            author_id=author.id,
            vote_count=1,
            created_at=datetime.now(UTC) + timedelta(hours=10),
        )
    )
    await db.commit()

    resp = await client.get("/feature-requests?sort=trending")
    assert resp.status_code == 200
    assert any(item["title"] == "Future dated" for item in resp.json()["items"])


async def test_pagination(client: AsyncClient, create_request: RequestFactory) -> None:
    for i in range(3):
        await create_request("ada", title=f"Feature number {i}")

    page1 = (await client.get("/feature-requests?page=1&page_size=2")).json()
    assert page1["total"] == 3
    assert len(page1["items"]) == 2
    assert page1["has_next"] is True

    page2 = (await client.get("/feature-requests?page=2&page_size=2")).json()
    assert len(page2["items"]) == 1
    assert page2["has_next"] is False
