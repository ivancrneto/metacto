"""Vote-integrity invariants — the core correctness of the domain."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from httpx import AsyncClient

RequestFactory = Callable[..., Awaitable[dict[str, Any]]]


async def test_upvote_increments_and_marks_voted(
    client: AsyncClient, create_request: RequestFactory
) -> None:
    req = await create_request("ada")
    resp = await client.post(f"/feature-requests/{req['id']}/votes", headers={"X-User": "linus"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["vote_count"] == 1
    assert body["has_voted"] is True


async def test_one_vote_per_user(client: AsyncClient, create_request: RequestFactory) -> None:
    req = await create_request("ada")
    url = f"/feature-requests/{req['id']}/votes"

    first = await client.post(url, headers={"X-User": "linus"})
    assert first.status_code == 201

    duplicate = await client.post(url, headers={"X-User": "linus"})
    assert duplicate.status_code == 409

    detail = await client.get(f"/feature-requests/{req['id']}")
    assert detail.json()["vote_count"] == 1  # count did not drift


async def test_concurrent_votes_only_one_succeeds(
    client: AsyncClient, create_request: RequestFactory
) -> None:
    req = await create_request("ada")
    url = f"/feature-requests/{req['id']}/votes"

    results = await asyncio.gather(
        client.post(url, headers={"X-User": "linus"}),
        client.post(url, headers={"X-User": "linus"}),
    )
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409]  # DB unique constraint holds under concurrency

    detail = await client.get(f"/feature-requests/{req['id']}")
    assert detail.json()["vote_count"] == 1


async def test_cannot_vote_own_request(client: AsyncClient, create_request: RequestFactory) -> None:
    req = await create_request("ada")
    resp = await client.post(f"/feature-requests/{req['id']}/votes", headers={"X-User": "ada"})
    assert resp.status_code == 403

    detail = await client.get(f"/feature-requests/{req['id']}")
    assert detail.json()["vote_count"] == 0


async def test_unvote_decrements(client: AsyncClient, create_request: RequestFactory) -> None:
    req = await create_request("ada")
    url = f"/feature-requests/{req['id']}/votes"
    await client.post(url, headers={"X-User": "linus"})

    resp = await client.delete(url, headers={"X-User": "linus"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["vote_count"] == 0
    assert body["has_voted"] is False


async def test_unvote_without_vote_returns_404(
    client: AsyncClient, create_request: RequestFactory
) -> None:
    req = await create_request("ada")
    resp = await client.delete(f"/feature-requests/{req['id']}/votes", headers={"X-User": "linus"})
    assert resp.status_code == 404


async def test_vote_on_missing_request_returns_404(client: AsyncClient) -> None:
    resp = await client.post("/feature-requests/9999/votes", headers={"X-User": "linus"})
    assert resp.status_code == 404
