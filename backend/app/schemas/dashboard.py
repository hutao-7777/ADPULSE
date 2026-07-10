"""Pydantic schemas for dashboard resources."""

from typing import List, Optional

from pydantic import BaseModel


class RTBSummary(BaseModel):
    total_auctions_today: int
    total_wins: int
    avg_winning_cpm: float
    fill_rate: float
    total_latency_avg_ms: float
    data_source: Optional[str] = None


class TrendPoint(BaseModel):
    label: str
    auctions: int
    wins: int
    win_rate: float
    avg_cpm: float
    data_source: Optional[str] = None


class WinRateTrend(BaseModel):
    period: str
    data: List[TrendPoint]
    data_source: Optional[str] = None


class KPICard(BaseModel):
    label: str
    value: float
    unit: str
    change: float
    trend: List[float]


class KPISummary(BaseModel):
    kpis: List[KPICard]
    data_source: Optional[str] = None
