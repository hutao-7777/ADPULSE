"""Unified daily stat aggregation model supporting multiple data sources."""

from __future__ import annotations

from datetime import date  # noqa: F401

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DailyStat(Base):
    __tablename__ = "daily_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_source: Mapped[str] = mapped_column(String, default="mock")
    date: Mapped[date] = mapped_column()  # noqa: F811
    total_bids: Mapped[int] = mapped_column(default=0)
    total_imps: Mapped[int] = mapped_column(default=0)
    total_clicks: Mapped[int] = mapped_column(default=0)
    total_convs: Mapped[int] = mapped_column(default=0)
    total_spend: Mapped[float] = mapped_column(default=0.0)
    avg_bid_price: Mapped[float] = mapped_column(nullable=True)
    avg_ctr: Mapped[float] = mapped_column(nullable=True)
    avg_cvr: Mapped[float] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("data_source", "date", name="uq_daily_stat_source_date"),
        Index("ix_daily_stats_source_date", "data_source", "date"),
    )
