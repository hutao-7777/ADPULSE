"""SQLAlchemy 2.0 domain models for AdPulse.

All primary keys use UUID. The runtime target is SQLite via aiosqlite.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.campaign import Campaign, Creative


class AuctionRequest(Base):
    __tablename__ = "auction_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    impression_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ssp: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    floor_price: Mapped[float] = mapped_column(Float, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    geo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign", back_populates="auction_requests"
    )
    bids: Mapped[List["AuctionBid"]] = relationship(
        "AuctionBid", back_populates="auction_request"
    )
    win: Mapped[Optional["AuctionWin"]] = relationship(
        "AuctionWin", back_populates="auction_request"
    )

    __table_args__ = (
        Index("ix_auction_requests_created_at", "created_at"),
        Index("ix_auction_requests_campaign_created", "campaign_id", "created_at"),
    )


class AuctionBid(Base):
    __tablename__ = "auction_bids"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auction_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("auction_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creatives.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dsp_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    bid_amount: Mapped[float] = mapped_column(Float, nullable=False)
    ctr_estimate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    auction_request: Mapped["AuctionRequest"] = relationship(
        "AuctionRequest", back_populates="bids"
    )
    creative: Mapped[Optional["Creative"]] = relationship(
        "Creative", back_populates="bids"
    )

    __table_args__ = (Index("ix_auction_bids_created_at", "created_at"),)


class AuctionWin(Base):
    __tablename__ = "auction_wins"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auction_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("auction_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creatives.id", ondelete="SET NULL"),
        nullable=True,
    )
    winning_bid: Mapped[float] = mapped_column(Float, nullable=False)
    second_price: Mapped[float] = mapped_column(Float, nullable=False)
    auction_type: Mapped[str] = mapped_column(
        String(50), default="second_price", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    auction_request: Mapped["AuctionRequest"] = relationship(
        "AuctionRequest", back_populates="win"
    )

    __table_args__ = (
        Index("ix_auction_wins_campaign_created", "campaign_id", "created_at"),
        UniqueConstraint("auction_request_id", name="uq_auction_wins_request"),
    )


# ---------------------------------------------------------------------------
# A/B testing domain
# ---------------------------------------------------------------------------
