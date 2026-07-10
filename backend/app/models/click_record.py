"""Unified click record model supporting multiple data sources."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ClickRecord(Base):
    __tablename__ = "click_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source: Mapped[str] = mapped_column(String, default="mock")
    click_id: Mapped[str] = mapped_column(String, index=True)
    bid_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column()
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    advertiser_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ipinyou_campaign_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("ix_click_records_data_source", "data_source"),
        Index("ix_click_records_timestamp", "timestamp"),
    )
