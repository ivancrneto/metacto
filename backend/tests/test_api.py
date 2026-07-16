"""API integration tests via TestClient — the submit -> list -> vote -> rank flow."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.main import app


def test_full_flow_submit_list_vote_and_rank(
    client_factory: Callable[[], TestClient],
) -> None:
    author = client_factory()
    voter = client_factory()  # a different X-Visitor-Id == a different user

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


def test_unvote_via_api_is_idempotent(client_factory: Callable[[], TestClient]) -> None:
    author = client_factory()
    voter = client_factory()

    rid = author.post("/api/requests", json={"title": "Removable", "description": "x"}).json()["id"]
    voter.post(f"/api/requests/{rid}/vote")

    removed = voter.delete(f"/api/requests/{rid}/vote")
    assert removed.status_code == 200
    assert removed.json() == {"request_id": rid, "vote_count": 0, "has_voted": False}

    # Removing again is a no-op, still 200 with count 0.
    assert voter.delete(f"/api/requests/{rid}/vote").json()["vote_count"] == 0


def test_missing_visitor_id_header_is_rejected(
    client_factory: Callable[[], TestClient],
) -> None:
    # client_factory activates the get_session override; build a client with no
    # X-Visitor-Id to confirm the identity requirement is enforced with a 400.
    client_factory()
    anon = TestClient(app)
    resp = anon.post("/api/requests/9999/vote")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Missing visitor identity"
