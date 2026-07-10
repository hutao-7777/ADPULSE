"""Unified bid record model supporting multiple data sources."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BidRecord(Base):
    __tablename__ = "bid_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source: Mapped[str] = mapped_column(String, default="mock")
    bid_id: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column()
    advertiser_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ad_slot: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    bid_price: Mapped[float] = mapped_column()
    pay_price: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_win: Mapped[bool] = mapped_column(default=False)
    # iPinYou-specific fields — nullable
    ipinyou_campaign_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ipinyou_creative_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ipinyou_region_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ipinyou_city_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Generic features
    device_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Metadata
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("ix_bid_records_data_source", "data_source"),
        Index("ix_bid_records_timestamp", "timestamp"),
        Index("ix_bid_records_source_time", "data_source", "timestamp"),
    )
