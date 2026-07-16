"""Ranking / popularity ordering.

Isolated behind a single function so the sort strategy is pluggable: a time-decay
"trending" score (see README) can be added here without touching the API layer.
The vote count is computed from the votes table (the source of truth) rather than
a denormalized counter, so it can never drift out of sync.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Select, asc, desc, func, select

from app.db.models import FeatureRequest, Vote


class SortKey(StrEnum):
    TOP = "top"
    NEW = "new"


def listing_query(sort: SortKey) -> Select[tuple[FeatureRequest, int]]:
    vote_count = func.count(Vote.id).label("vote_count")
    stmt = (
        select(FeatureRequest, vote_count)
        .outerjoin(Vote, Vote.request_id == FeatureRequest.id)
        .group_by(FeatureRequest.id)
    )
    if sort is SortKey.NEW:
        return stmt.order_by(desc(FeatureRequest.created_at), desc(FeatureRequest.id))
    # TOP: most-voted first; oldest wins ties (rewards early traction). The final
    # id tie-break keeps ordering stable when timestamps collide.
    return stmt.order_by(desc(vote_count), asc(FeatureRequest.created_at), asc(FeatureRequest.id))
