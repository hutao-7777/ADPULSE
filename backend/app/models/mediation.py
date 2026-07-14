"""SDK Platform — AdNetwork, AdSource, ImpressionEvent, ClickEvent 域模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now


class AdNetwork(Base):
    """广告网络定义 — 如 AdMob, Meta, Unity Ads 等。"""
    __tablename__ = "ad_networks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    adapter_class: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supports_bidding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    ad_sources: Mapped[List["AdSource"]] = relationship("AdSource", back_populates="ad_network")


class AdSource(Base):
    """广告源实例 — AdUnit 关联的一个具体广告网络配置。"""
    __tablename__ = "ad_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_unit_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("ad_units.id", ondelete="CASCADE"), nullable=False, index=True)
    ad_network_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("ad_networks.id", ondelete="CASCADE"), nullable=False, index=True)
    instance_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ecpm: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    floor_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bidding_endpoint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    credentials: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    ad_unit: Mapped["AdUnit"] = relationship("AdUnit", back_populates="ad_sources")
    ad_network: Mapped["AdNetwork"] = relationship("AdNetwork", back_populates="ad_sources")
    __table_args__ = (Index("ix_ad_sources_unit_network", "ad_unit_id", "ad_network_id"),)


class ImpressionEvent(Base):
    __tablename__ = "impression_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("ad_units.id", ondelete="SET NULL"), nullable=True, index=True)
    app_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("apps.id", ondelete="SET NULL"), nullable=True, index=True)
    publisher_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("publishers.id", ondelete="SET NULL"), nullable=True, index=True)
    ad_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("ad_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    network_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    impression_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    viewability_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    viewability_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_impression_events_created", "created_at"),)


class ClickEvent(Base):
    __tablename__ = "click_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    impression_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    ad_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    ad_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    network_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    click_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    redirect_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (Index("ix_click_events_created", "created_at"),)
