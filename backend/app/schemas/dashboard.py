"""Pydantic schemas for dashboard resources."""

from pydantic import BaseModel
from typing import List


class RTBSummary(BaseModel):
    total_auctions_today: int
    total_wins: int
    avg_winning_cpm: float
    fill_rate: float
    total_latency_avg_ms: float


class TrendPoint(BaseModel):
    label: str
    auctions: int
    wins: int
    win_rate: float
    avg_cpm: float


class WinRateTrend(BaseModel):
    period: str
    data: List[TrendPoint]
