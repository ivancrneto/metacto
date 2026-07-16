"""Pydantic request/response schemas — the HTTP contract.

Validation (length limits, whitespace stripping) lives here at the edge so bad
input never reaches the domain or the database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator
from whenever import Instant, PlainDateTime

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
        # Normalize through whenever, then hand Pydantic a stdlib datetime back.
        # SQLite returns naive datetimes we always store as UTC, so assume UTC;
        # Postgres returns tz-aware values, which we convert to UTC. Either way the
        # client gets an explicit offset.
        instant = PlainDateTime(value).assume_utc() if value.tzinfo is None else Instant(value)
        return instant.to_stdlib()


class VoteOut(BaseModel):
    request_id: int
    vote_count: int
    has_voted: bool
