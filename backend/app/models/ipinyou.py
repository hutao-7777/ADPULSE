"""SQLAlchemy models for the iPinYou RTB dataset."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class IpinyouBid(Base):
    """A single bid request/response from the iPinYou RTB dataset."""

    __tablename__ = "ipinyou_bids"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bid_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, index=True
    )
    ipinyou_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    region: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    city: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_exchange: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anonymous_url_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ad_slot_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ad_slot_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_slot_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_slot_visibility: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ad_slot_format: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    creative_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bidding_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    paying_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    landing_page_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    advertiser_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )
    user_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_win: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_clicked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_converted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_ipinyou_bids_adv_ts", "advertiser_id", "timestamp"),
        Index("ix_ipinyou_bids_win", "is_win", "advertiser_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<IpinyouBid(bid_id={self.bid_id!r}, advertiser={self.advertiser_id}, "
            f"price={self.bidding_price}, win={self.is_win})>"
        )


class IpinyouImp(Base):
    """A won impression from the iPinYou dataset."""

    __tablename__ = "ipinyou_imps"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bid_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
    ipinyou_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    region: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    city: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_exchange: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anonymous_url_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ad_slot_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ad_slot_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_slot_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_slot_visibility: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ad_slot_format: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    creative_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bid_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    paying_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    landing_page_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    advertiser_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )
    user_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    __table_args__ = (Index("ix_ipinyou_imps_adv_ts", "advertiser_id", "timestamp"),)

    def __repr__(self) -> str:
        return f"<IpinyouImp(bid_id={self.bid_id!r}, advertiser={self.advertiser_id})>"


class IpinyouClick(Base):
    """A click event from the iPinYou dataset."""

    __tablename__ = "ipinyou_clicks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bid_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
    ipinyou_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    region: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    city: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_exchange: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anonymous_url_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ad_slot_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ad_slot_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_slot_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_slot_visibility: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ad_slot_format: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    creative_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bidding_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    paying_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    landing_page_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    advertiser_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )
    user_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    __table_args__ = (Index("ix_ipinyou_clicks_adv_ts", "advertiser_id", "timestamp"),)

    def __repr__(self) -> str:
        return (
            f"<IpinyouClick(bid_id={self.bid_id!r}, advertiser={self.advertiser_id})>"
        )


class IpinyouConv(Base):
    """A conversion event from the iPinYou dataset."""

    __tablename__ = "ipinyou_convs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bid_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False
    )
    ipinyou_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    region: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    city: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_exchange: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anonymous_url_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ad_slot_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ad_slot_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_slot_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ad_slot_visibility: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    ad_slot_format: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    creative_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    bidding_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    paying_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    landing_page_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    advertiser_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, index=True
    )
    user_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    __table_args__ = (Index("ix_ipinyou_convs_adv_ts", "advertiser_id", "timestamp"),)

    def __repr__(self) -> str:
        return f"<IpinyouConv(bid_id={self.bid_id!r}, advertiser={self.advertiser_id})>"


class IpinyouDailyStat(Base):
    """Daily aggregated statistics for the iPinYou dataset."""

    __tablename__ = "ipinyou_daily_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    advertiser_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_ctr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_ipinyou_daily_stats_date_adv", "date", "advertiser_id", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<IpinyouDailyStat(date={self.date}, advertiser={self.advertiser_id}, "
            f"impressions={self.impressions}, clicks={self.clicks}, "
            f"ctr={self.avg_ctr:.4f})>"
        )
