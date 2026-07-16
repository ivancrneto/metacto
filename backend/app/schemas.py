"""Pydantic request/response schemas — the HTTP contract.

Validation (length limits, whitespace stripping) lives here at the edge so bad
input never reaches the domain or the database.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]


class RequestCreate(BaseModel):
    title: Title
    description: Description


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    created_at: datetime
    vote_count: int
    has_voted: bool
    is_author: bool

    @field_validator("created_at")
    @classmethod
    def _as_utc(cls, value: datetime) -> datetime:
        # SQLite returns naive datetimes; we always store UTC, so stamp it as UTC
        # (Postgres returns tz-aware). Either way the client gets an explicit offset.
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class VoteOut(BaseModel):
    request_id: int
    vote_count: int
    has_voted: bool
