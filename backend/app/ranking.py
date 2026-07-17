"""Ranking strategies. See ADR-0001 for the rationale and the trending formula."""

from sqlalchemy import Select, func

from .config import settings
from .models import FeatureRequest
from .schemas import SortMode


def apply_sort(
    stmt: Select[tuple[FeatureRequest]], sort: SortMode
) -> Select[tuple[FeatureRequest]]:
    """Attach an ORDER BY to a feature-request query for the given sort mode.

    ``id DESC`` is always the final tiebreak so pagination is stable when other
    keys collide.
    """
    if sort is SortMode.new:
        return stmt.order_by(FeatureRequest.created_at.desc(), FeatureRequest.id.desc())

    if sort is SortMode.trending:
        # Reddit/HN-style decay: recent votes outweigh old ones.
        #   score = votes / (age_hours + 2) ^ gravity
        # Clamp the base to >= 1 so a future-dated created_at (clock skew, imports)
        # can't produce a negative base — Postgres errors on power(negative, fractional).
        age_hours = func.extract("epoch", func.now() - FeatureRequest.created_at) / 3600.0
        base = func.greatest(age_hours + 2.0, 1.0)
        score = FeatureRequest.vote_count / func.power(base, settings.trending_gravity)
        return stmt.order_by(
            score.desc(), FeatureRequest.created_at.desc(), FeatureRequest.id.desc()
        )

    # SortMode.top (default)
    return stmt.order_by(
        FeatureRequest.vote_count.desc(),
        FeatureRequest.created_at.desc(),
        FeatureRequest.id.desc(),
    )
