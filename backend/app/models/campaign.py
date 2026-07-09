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
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.abtest import Experiment
    from app.models.attribution import Touchpoint
    from app.models.rtb import AuctionBid, AuctionRequest
    from app.models.user import User

campaign_audience_segments = Table(
    "campaign_audience_segments",
    Base.metadata,
    Column(
        "campaign_id",
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "audience_segment_id",
        Uuid(as_uuid=True),
        ForeignKey("audience_segments.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Advertiser(Base):
    __tablename__ = "advertisers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    owner: Mapped["User"] = relationship("User", back_populates="advertisers")
    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", back_populates="advertiser"
    )


class AudienceSegment(Base):
    __tablename__ = "audience_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    estimated_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign",
        secondary=campaign_audience_segments,
        back_populates="audience_segments",
    )


class BiddingStrategy(Base):
    __tablename__ = "bidding_strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g. "manual_cpc", "target_cpa", "roi"
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign", back_populates="bidding_strategy"
    )


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    advertiser_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("advertisers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    bidding_strategy_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bidding_strategies.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", nullable=False, index=True
    )  # draft, active, paused, archived
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    daily_budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    target_cpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_roas: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    frequency_cap: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    advertiser: Mapped[Optional["Advertiser"]] = relationship(
        "Advertiser", back_populates="campaigns"
    )
    bidding_strategy: Mapped[Optional["BiddingStrategy"]] = relationship(
        "BiddingStrategy", back_populates="campaigns"
    )
    audience_segments: Mapped[List["AudienceSegment"]] = relationship(
        "AudienceSegment",
        secondary=campaign_audience_segments,
        back_populates="campaigns",
    )
    creatives: Mapped[List["Creative"]] = relationship(
        "Creative", back_populates="campaign"
    )
    experiments: Mapped[List["Experiment"]] = relationship(
        "Experiment", back_populates="campaign"
    )
    daily_metrics: Mapped[List["DailyMetric"]] = relationship(
        "DailyMetric", back_populates="campaign"
    )
    touchpoints: Mapped[List["Touchpoint"]] = relationship(
        "Touchpoint", back_populates="campaign"
    )
    auction_requests: Mapped[List["AuctionRequest"]] = relationship(
        "AuctionRequest", back_populates="campaign"
    )

    __table_args__ = (
        Index("ix_campaigns_status_dates", "status", "start_date", "end_date"),
        Index("ix_campaigns_advertiser_status", "advertiser_id", "status"),
    )


class Creative(Base):
    __tablename__ = "creatives"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    asset_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    size: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    call_to_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    predicted_ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fatigue_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign", back_populates="creatives"
    )
    bids: Mapped[List["AuctionBid"]] = relationship(
        "AuctionBid", back_populates="creative"
    )

    __table_args__ = (
        Index("ix_creatives_campaign_active", "campaign_id", "is_active"),
        Index("ix_creatives_upload_time", "created_at"),
    )


# ---------------------------------------------------------------------------
# RTB auction domain
# ---------------------------------------------------------------------------


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    spend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cpm: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cpc: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    roi: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="daily_metrics"
    )

    __table_args__ = (
        Index("ix_daily_metrics_date_campaign", "date", "campaign_id"),
        UniqueConstraint("date", "campaign_id", name="uq_daily_metric_date_campaign"),
    )


# ---------------------------------------------------------------------------
# Agent domain
# ---------------------------------------------------------------------------
