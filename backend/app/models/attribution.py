"""SQLAlchemy 2.0 domain models for AdPulse.

All primary keys use UUID. The runtime target is SQLite via aiosqlite.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.campaign import Campaign


class ConversionEvent(Base):
    __tablename__ = "conversion_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    conversion_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )
    channel: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    geo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    creative_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creatives.id", ondelete="SET NULL"),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    touchpoints: Mapped[List["Touchpoint"]] = relationship(
        "Touchpoint", back_populates="conversion_event"
    )
    attribution_results: Mapped[List["AttributionResult"]] = relationship(
        "AttributionResult", back_populates="conversion_event"
    )

    __table_args__ = (
        Index("ix_conversion_events_user_time", "user_id", "conversion_time"),
        Index("ix_conversion_events_campaign_time", "campaign_id", "conversion_time"),
    )


class Touchpoint(Base):
    __tablename__ = "touchpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
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
    touchpoint_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # impression, click, view
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )
    conversion_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversion_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="touchpoints"
    )
    conversion_event: Mapped[Optional["ConversionEvent"]] = relationship(
        "ConversionEvent", back_populates="touchpoints"
    )

    __table_args__ = (
        Index(
            "ix_touchpoints_user_campaign_seq",
            "user_id",
            "campaign_id",
            "touchpoint_seq",
        ),
        Index("ix_touchpoints_event_time", "event_time"),
        Index("ix_touchpoints_conversion", "conversion_event_id"),
    )


class AttributionResult(Base):
    __tablename__ = "attribution_results"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversion_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversion_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # shapley, linear, last_click, etc.
    click_window_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    view_window_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    channel_credits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    campaign_credits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    conversion_event: Mapped["ConversionEvent"] = relationship(
        "ConversionEvent", back_populates="attribution_results"
    )

    __table_args__ = (
        Index(
            "ix_attribution_results_conversion_model",
            "conversion_event_id",
            "model_type",
        ),
        Index("ix_attribution_results_calculated_at", "calculated_at"),
    )


# ---------------------------------------------------------------------------
# Traffic quality domain
# ---------------------------------------------------------------------------


class TrafficQualityScore(Base):
    __tablename__ = "traffic_quality_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
    flags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_traffic_quality_scores_campaign_date", "campaign_id", "date"),
        Index("ix_traffic_quality_scores_date", "date"),
    )


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_fraud_alerts_campaign_status", "campaign_id", "status"),
        Index("ix_fraud_alerts_detected_at", "detected_at"),
    )


# ---------------------------------------------------------------------------
# Dashboard / reporting
# ---------------------------------------------------------------------------
