"""API integration tests via TestClient — the submit -> list -> vote -> rank flow."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient


def test_full_flow_submit_list_vote_and_rank(
    client_factory: Callable[[], TestClient],
) -> None:
    author = client_factory()
    voter = client_factory()  # a different cookie jar == a different user

    assert author.get("/api/requests").json() == []

    created = author.post(
        "/api/requests",
        json={"title": "Add SSO", "description": "Support SAML/OIDC login."},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["vote_count"] == 0
    assert body["is_author"] is True
    request_id = body["id"]

    # The author cannot upvote their own request.
    assert author.post(f"/api/requests/{request_id}/vote").status_code == 403

    # A different user can, and the count reflects it.
    voted = voter.post(f"/api/requests/{request_id}/vote")
    assert voted.status_code == 200
    assert voted.json() == {"request_id": request_id, "vote_count": 1, "has_voted": True}

    # has_voted is per-identity.
    assert voter.get("/api/requests").json()[0]["has_voted"] is True
    assert author.get("/api/requests").json()[0]["has_voted"] is False


def test_ranking_reflects_votes(client_factory: Callable[[], TestClient]) -> None:
    author = client_factory()
    voter = client_factory()

    author.post("/api/requests", json={"title": "Low", "description": "x"})
    high = author.post("/api/requests", json={"title": "High", "description": "y"}).json()

    voter.post(f"/api/requests/{high['id']}/vote")

    top = voter.get("/api/requests?sort=top").json()
    assert [r["title"] for r in top] == ["High", "Low"]


def test_validation_rejects_bad_input(client: TestClient) -> None:
    short_title = client.post("/api/requests", json={"title": "ab", "description": "x"})
    assert short_title.status_code == 422
    empty_desc = client.post("/api/requests", json={"title": "ok title", "description": ""})
    assert empty_desc.status_code == 422


def test_voting_unknown_request_is_404(client: TestClient) -> None:
    assert client.post("/api/requests/9999/vote").status_code == 404
