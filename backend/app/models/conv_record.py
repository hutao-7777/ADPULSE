"""Unified conversion record model supporting multiple data sources."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ConvRecord(Base):
    __tablename__ = "conv_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source: Mapped[str] = mapped_column(String, default="mock")
    conv_id: Mapped[str] = mapped_column(String, index=True)
    click_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    bid_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column()
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    advertiser_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    conv_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    conv_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    ipinyou_campaign_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("ix_conv_records_data_source", "data_source"),
        Index("ix_conv_records_timestamp", "timestamp"),
    )
