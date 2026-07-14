"""SDK Platform — ConversionEvent, Touchpoint, Attribution, TrafficQuality 域模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


class ConversionEvent(Base):
    """安装/转化事件 — 用于归因匹配。"""

    __tablename__ = "conversion_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    click_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    impression_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    device_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    ad_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ad_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    app_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("apps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    attributed_network: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    attribution_model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    touchpoints: Mapped[List["Touchpoint"]] = relationship(
        "Touchpoint", back_populates="conversion_event"
    )
    attribution_results: Mapped[List["AttributionResult"]] = relationship(
        "AttributionResult", back_populates="conversion_event"
    )

    __table_args__ = (Index("ix_conv_events_device_type", "device_id", "event_type"),)


class Touchpoint(Base):
    """用户触点 — 一个转化前的广告交互序列。"""

    __tablename__ = "touchpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ad_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ad_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    app_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("apps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    touchpoint_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
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

    conversion_event: Mapped[Optional["ConversionEvent"]] = relationship(
        "ConversionEvent", back_populates="touchpoints"
    )

    __table_args__ = (
        Index(
            "ix_touchpoints_user_adunit_seq", "user_id", "ad_unit_id", "touchpoint_seq"
        ),
        Index("ix_touchpoints_event_time", "event_time"),
    )


class AttributionResult(Base):
    """归因结果 — 每次归因计算的结果。"""

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
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    click_window_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    view_window_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    channel_credits: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
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
    )


class TrafficQualityScore(Base):
    """流量质量评分。"""

    __tablename__ = "traffic_quality_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ad_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ad_units.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    grade: Mapped[str] = mapped_column(String(20), default="standard", nullable=False)
    flags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    anomaly_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ctr_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cvr_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    bounce_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dwell_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    interaction_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    __table_args__ = (Index("ix_traffic_quality_ad_unit_date", "ad_unit_id", "date"),)


class FraudAlert(Base):
    """作弊告警。"""

    __tablename__ = "fraud_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ad_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ad_units.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False, index=True
    )

    __table_args__ = (Index("ix_fraud_alerts_ad_unit_status", "ad_unit_id", "status"),)
