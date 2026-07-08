"""Pydantic schemas for RTB simulation."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ImpressionSpec(BaseModel):
    floor_price: float = Field(..., ge=0, description="Publisher floor price per impression")
    user_segments: List[str] = Field(default_factory=list)
    device_type: str = Field(..., pattern="^(mobile|desktop|tablet)$")
    geo: str = Field(..., pattern="^(tier1|tier2|tier3)$")
    ad_format: str = Field(..., pattern="^(banner_300x250|native|video_15s)$")
    context_category: str = "news"


class SingleAuctionRequest(ImpressionSpec):
    auction_type: str = Field(..., pattern="^(first_price|second_price)$")


class BatchAuctionRequest(BaseModel):
    count: int = Field(..., ge=1, le=10000)
    auction_type: str = Field(default="second_price", pattern="^(first_price|second_price)$")
    campaign_config: dict = Field(default_factory=dict)


class BidEntry(BaseModel):
    dsp: str
    bid: float
    response_time_ms: int


class WinnerInfo(BaseModel):
    dsp: str
    winning_bid: float
    settlement_price: float


class AuctionResult(BaseModel):
    impression_id: str
    floor_price: float
    auction_type: str
    total_bids: int
    bids: List[BidEntry]
    winner: Optional[WinnerInfo]
    reason: Optional[str] = None
    latency_ms: int
    timestamp: str


class BatchAuctionResponse(BaseModel):
    count: int
    results: List[AuctionResult]
    stats: dict


class DSPStatus(BaseModel):
    name: str
    budget_remaining: float
    target_segments: List[str]
    max_cpm: float
    pacing_rate: float
    bidding_strategy: str


class DSPConfigUpdate(BaseModel):
    bidding_strategy: Optional[str] = Field(None, pattern="^(aggressive|balanced|conservative)$")
    budget_remaining: Optional[float] = Field(None, ge=0)
    target_segments: Optional[List[str]] = None
    max_cpm: Optional[float] = Field(None, ge=0)
    pacing_rate: Optional[float] = Field(None, ge=0, le=1)
