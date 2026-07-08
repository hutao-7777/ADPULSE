import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Float,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy import Uuid as SQLiteUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Creative(Base):
    __tablename__ = "creatives"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    ai_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    predicted_ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fatigue_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (
        Index("ix_creative_upload_time", "upload_time"),
        Index("ix_creative_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Creative(id={self.id}, name={self.name!r})>"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="paused", nullable=False)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    spent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    target_cpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    auctions: Mapped[List["Auction"]] = relationship("Auction", back_populates="campaign")
    ab_tests: Mapped[List["ABTest"]] = relationship("ABTest", back_populates="campaign")
    daily_metrics: Mapped[List["DailyMetric"]] = relationship(
        "DailyMetric", back_populates="campaign"
    )
    touchpoints: Mapped[List["Touchpoint"]] = relationship(
        "Touchpoint", back_populates="campaign"
    )

    __table_args__ = (
        Index("ix_campaign_status", "status"),
        Index("ix_campaign_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name={self.name!r}, status={self.status!r})>"


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    impression_id: Mapped[str] = mapped_column(String(255), nullable=False)
    floor_price: Mapped[float] = mapped_column(Float, nullable=False)
    winning_bid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    winning_dsp: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    auction_type: Mapped[str] = mapped_column(
        String(50), default="first_price", nullable=False
    )
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="auctions")
    bids: Mapped[List["BidRecord"]] = relationship("BidRecord", back_populates="auction")

    __table_args__ = (
        Index("ix_auction_campaign_id", "campaign_id"),
        Index("ix_auction_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Auction(id={self.id}, campaign_id={self.campaign_id}, impression_id={self.impression_id!r})>"


class BidRecord(Base):
    __tablename__ = "bid_records"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    auction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auctions.id", ondelete="CASCADE"),
        nullable=False,
    )
    dsp_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bid_amount: Mapped[float] = mapped_column(Float, nullable=False)
    ctr_estimate: Mapped[float] = mapped_column(Float, nullable=False)
    was_winner: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    auction: Mapped["Auction"] = relationship("Auction", back_populates="bids")

    __table_args__ = (
        Index("ix_bid_record_auction_id", "auction_id"),
        Index("ix_bid_record_dsp_name", "dsp_name"),
    )

    def __repr__(self) -> str:
        return f"<BidRecord(id={self.id}, auction_id={self.auction_id}, dsp_name={self.dsp_name!r})>"


class ABTest(Base):
    __tablename__ = "ab_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    traffic_split: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    metric_target: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    winner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="ab_tests")
    variants: Mapped[List["ABTestVariant"]] = relationship(
        "ABTestVariant", back_populates="ab_test"
    )

    __table_args__ = (
        Index("ix_ab_test_campaign_id", "campaign_id"),
        Index("ix_ab_test_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ABTest(id={self.id}, name={self.name!r}, campaign_id={self.campaign_id})>"


class ABTestVariant(Base):
    __tablename__ = "ab_test_variants"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ab_test_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ab_tests.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    traffic_pct: Mapped[float] = mapped_column(Float, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    ab_test: Mapped["ABTest"] = relationship("ABTest", back_populates="variants")

    __table_args__ = (
        Index("ix_ab_test_variant_ab_test_id", "ab_test_id"),
        Index("ix_ab_test_variant_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<ABTestVariant(id={self.id}, ab_test_id={self.ab_test_id}, name={self.name!r})>"


class ConversionEvent(Base):
    __tablename__ = "conversion_events"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    conversion_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    geo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("creatives.id", ondelete="SET NULL"),
        nullable=True,
    )

    touchpoints: Mapped[List["Touchpoint"]] = relationship(
        "Touchpoint", back_populates="conversion_event"
    )
    attribution_results: Mapped[List["AttributionResult"]] = relationship(
        "AttributionResult", back_populates="conversion_event"
    )

    __table_args__ = (
        Index("ix_conversion_event_user_id", "user_id"),
        Index("ix_conversion_event_campaign_id", "campaign_id"),
        Index("ix_conversion_event_conversion_time", "conversion_time"),
    )


class Touchpoint(Base):
    __tablename__ = "touchpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    touchpoint_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    conversion_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("conversion_events.id", ondelete="SET NULL"),
        nullable=True,
    )

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="touchpoints")
    conversion_event: Mapped[Optional["ConversionEvent"]] = relationship(
        "ConversionEvent", back_populates="touchpoints"
    )

    __table_args__ = (
        Index("ix_touchpoint_user_id", "user_id"),
        Index("ix_touchpoint_campaign_id", "campaign_id"),
        Index("ix_touchpoint_event_time", "event_time"),
        Index("ix_touchpoint_user_campaign_seq", "user_id", "campaign_id", "touchpoint_seq"),
    )


class AttributionResult(Base):
    __tablename__ = "attribution_results"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversion_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversion_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    channel_credits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    conversion_event: Mapped["ConversionEvent"] = relationship(
        "ConversionEvent", back_populates="attribution_results"
    )

    __table_args__ = (
        Index("ix_attribution_result_conversion_event_id", "conversion_event_id"),
        Index("ix_attribution_result_model_type", "model_type"),
    )


class TrafficQualityScore(Base):
    __tablename__ = "traffic_quality_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    geo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)
    ctr_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cvr_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bounce_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dwell_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    interaction_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_traffic_quality_score_campaign_id", "campaign_id"),
        Index("ix_traffic_quality_score_date", "date"),
        Index("ix_traffic_quality_score_campaign_date", "campaign_id", "date"),
    )


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)

    __table_args__ = (
        Index("ix_fraud_alert_campaign_id", "campaign_id"),
        Index("ix_fraud_alert_status", "status"),
        Index("ix_fraud_alert_detected_at", "detected_at"),
    )


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLiteUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
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

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="daily_metrics")

    __table_args__ = (
        Index("ix_daily_metric_date", "date"),
        Index("ix_daily_metric_campaign_id", "campaign_id"),
        Index("ix_daily_metric_date_campaign", "date", "campaign_id"),
    )

    def __repr__(self) -> str:
        return f"<DailyMetric(id={self.id}, date={self.date}, campaign_id={self.campaign_id})>"
