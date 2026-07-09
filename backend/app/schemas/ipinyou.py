"""Pydantic schemas for iPinYou RTB dataset APIs."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IpinyouBidOut(BaseModel):
    """Public representation of a bid record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bid_id: str
    timestamp: datetime
    advertiser_id: Optional[str]
    region: Optional[int]
    city: Optional[int]
    ad_exchange: Optional[int]
    ad_slot_id: Optional[str]
    creative_id: Optional[str]
    bidding_price: float
    paying_price: float
    is_win: bool
    is_clicked: bool
    is_converted: bool


class IpinyouImpOut(BaseModel):
    """Public representation of an impression record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bid_id: str
    timestamp: datetime
    advertiser_id: Optional[str]
    bid_price: float
    paying_price: float
    creative_id: Optional[str]


class IpinyouClickOut(BaseModel):
    """Public representation of a click record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bid_id: str
    timestamp: datetime
    advertiser_id: Optional[str]


class IpinyouConvOut(BaseModel):
    """Public representation of a conversion record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bid_id: str
    timestamp: datetime
    advertiser_id: Optional[str]


class IpinyouBidDetailOut(IpinyouBidOut):
    """Bid detail including related impression, click and conversion."""

    impression: Optional[IpinyouImpOut] = None
    click: Optional[IpinyouClickOut] = None
    conversion: Optional[IpinyouConvOut] = None


class IpinyouDailyStatOut(BaseModel):
    """Public representation of a daily statistic record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date: date
    advertiser_id: Optional[str]
    impressions: int
    clicks: int
    conversions: int
    total_cost: float
    avg_ctr: float


class IpinyouSummaryOut(BaseModel):
    """High-level summary across the imported iPinYou dataset."""

    total_bids: int
    total_impressions: int
    total_clicks: int
    total_conversions: int
    total_cost: float
    avg_ctr: float
    avg_cpm: float


class IpinyouAuctionListOut(BaseModel):
    """Paginated list of auction records."""

    total: int
    page: int
    page_size: int
    items: List[IpinyouBidOut]
