"""Bidding Server - In-App Bidding server endpoint."""

import time
import uuid
from typing import List, Optional

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.models import AdNetwork, AdSource, AdUnit

router = APIRouter(prefix="/v1", tags=["bidding"])


class BidRequestPayload(BaseModel):
    publisher_key: str = Field(..., min_length=1)
    ad_unit_id: str = Field(..., min_length=1)
    device_id: Optional[str] = None
    user_agent: Optional[str] = None
    url: Optional[str] = None
    sdk_version: Optional[str] = None


class BidResponsePayload(BaseModel):
    ad_unit_id: str
    network_name: str
    network_display_name: str
    price: float
    currency: str
    creative_html: Optional[str] = None
    click_url: Optional[str] = None
    imp_url: Optional[str] = None
    source_type: str
    bid_id: str


@router.post("/bid", response_model=BidResponsePayload)
async def request_bid(
    body: BidRequestPayload,
    db: AsyncSession = Depends(get_db),
):
    start = time.perf_counter()
    ad_unit_id = uuid.UUID(body.ad_unit_id) if body.ad_unit_id else None
    if not ad_unit_id:
        return _fallback_response(body.ad_unit_id, "no_bidders")

    result = await db.execute(
        select(AdSource)
        .where(AdSource.ad_unit_id == ad_unit_id, AdSource.status == "active")
        .order_by(AdSource.priority.asc())
        .limit(5)
    )
    sources = list(result.scalars().all())
    if not sources:
        return _fallback_response(body.ad_unit_id, "no_sources")

    au = await db.get(AdUnit, ad_unit_id)
    bidding_config = au.bidding_config if au and isinstance(au.bidding_config, dict) else {}
    waterfall_sources = [s for s in sources if not s.bidding_endpoint]
    bidding_sources = [s for s in sources if s.bidding_endpoint]
    waterfall_sources.sort(key=lambda s: s.ecpm, reverse=True)
    bidding_sources.sort(key=lambda s: s.ecpm, reverse=True)

    best_bid = None
    best_source = None
    for bs in bidding_sources:
        bid_ecpm = bs.ecpm * 1.1
        if best_bid is None or bid_ecpm > best_bid:
            best_bid = bid_ecpm
            best_source = bs
    if waterfall_sources and waterfall_sources[0].ecpm > (best_bid or 0):
        best_bid = waterfall_sources[0].ecpm
        best_source = waterfall_sources[0]

    if best_source is None or best_bid is None:
        return _fallback_response(body.ad_unit_id, "no_bidders")

    network = await db.get(AdNetwork, best_source.ad_network_id)
    network_name = network.name if network else best_source.instance_name
    network_display = network.display_name if network else best_source.instance_name

    return BidResponsePayload(
        ad_unit_id=body.ad_unit_id,
        network_name=network_name,
        network_display_name=network_display or network_name,
        price=best_bid,
        currency="USD",
        creative_html=f"<!-- Ad from {network_name} --><div>Sponsored</div>",
        click_url=f"https://click.adpulse.com/{uuid.uuid4().hex[:12]}",
        source_type="bidding" if best_source.bidding_endpoint else "waterfall",
        bid_id=f"bid-{uuid.uuid4().hex[:16]}",
    )


def _fallback_response(ad_unit_id: str, reason: str) -> BidResponsePayload:
    return BidResponsePayload(
        ad_unit_id=ad_unit_id,
        network_name="fallback",
        network_display_name="Fallback Ad",
        price=0.0,
        currency="USD",
        creative_html=None,
        click_url=None,
        source_type="fallback",
        bid_id=f"bid-{uuid.uuid4().hex[:16]}",
    )
