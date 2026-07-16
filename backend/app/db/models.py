"""SQLAlchemy 2.0 ORM models.

The DB models are intentionally separate from the Pydantic API schemas
(app/schemas.py) so the storage shape can evolve without leaking into the HTTP
contract, and vice versa.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class FeatureRequest(Base):
    __tablename__ = "feature_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    # Anonymous author identity (hashed browser fingerprint); used to block self-votes.
    author_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    votes: Mapped[list[Vote]] = relationship(back_populates="request", cascade="all, delete-orphan")


class Vote(Base):
    __tablename__ = "votes"
    # One vote per (voter, request) enforced at the database layer — the integrity
    # of the vote counts is a data invariant, not application logic we can forget.
    __table_args__ = (UniqueConstraint("voter_id", "request_id", name="uq_vote_voter_request"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("feature_requests.id", ondelete="CASCADE"), index=True
    )
    voter_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    request: Mapped[FeatureRequest] = relationship(back_populates="votes")
