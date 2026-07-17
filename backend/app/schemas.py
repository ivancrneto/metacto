from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .models import FeatureRequest


class SortMode(StrEnum):
    top = "top"  # most votes first (recency tiebreak)
    new = "new"  # newest first
    trending = "trending"  # time-decayed popularity


class FeatureRequestCreate(BaseModel):
    # Strip surrounding whitespace before length checks so "   " is rejected.
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=1, max_length=5000)


class FeatureRequestOut(BaseModel):
    id: int
    title: str
    description: str
    author: str
    vote_count: int
    has_voted: bool
    created_at: datetime


class Page(BaseModel):
    items: list[FeatureRequestOut]
    total: int
    page: int
    page_size: int
    has_next: bool


def feature_request_out(fr: FeatureRequest, *, has_voted: bool) -> FeatureRequestOut:
    """Serialize an ORM request (with its author eager-loaded) for the API."""
    return FeatureRequestOut(
        id=fr.id,
        title=fr.title,
        description=fr.description,
        author=fr.author.username,
        vote_count=fr.vote_count,
        has_voted=has_voted,
        created_at=fr.created_at,
    )
