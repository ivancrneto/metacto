"""Input-validation and identity invariants."""

import pytest
from httpx import AsyncClient


@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("ab", "valid description"),  # title shorter than 3
        ("   ", "valid description"),  # blank title (stripped -> empty)
        ("valid title", ""),  # empty description
        ("valid title", "   "),  # blank description (stripped -> empty)
    ],
)
async def test_create_rejects_invalid_payload(
    client: AsyncClient, title: str, description: str
) -> None:
    resp = await client.post(
        "/feature-requests",
        headers={"X-User": "ada"},
        json={"title": title, "description": description},
    )
    assert resp.status_code == 422


async def test_create_missing_title_field(client: AsyncClient) -> None:
    resp = await client.post(
        "/feature-requests",
        headers={"X-User": "ada"},
        json={"description": "no title provided"},
    )
    assert resp.status_code == 422


async def test_create_requires_identity(client: AsyncClient) -> None:
    resp = await client.post(
        "/feature-requests",
        json={"title": "valid title", "description": "desc"},
    )
    assert resp.status_code == 401


async def test_invalid_username_rejected(client: AsyncClient) -> None:
    resp = await client.post(
        "/feature-requests",
        headers={"X-User": "bad user!"},
        json={"title": "valid title", "description": "desc"},
    )
    assert resp.status_code == 422
