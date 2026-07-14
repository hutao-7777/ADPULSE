"""SDK Config delivery API."""

import uuid
from typing import List

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.models import AdNetwork, AdSource, AdUnit

router = APIRouter(prefix="/v1/sdk", tags=["sdk_config"])


class WaterfallEntry(BaseModel):
    source_id: str
    network_name: str
    ecpm: float
    priority: int
    timeout_ms: int = 500


class BiddingEntry(BaseModel):
    source_id: str
    network_name: str
    endpoint: str | None
    timeout_ms: int = 500


class SdkAdUnitConfig(BaseModel):
    ad_unit_id: str
    ad_format: str
    width: int | None
    height: int | None
    waterfall: List[WaterfallEntry]
    bidding: List[BiddingEntry]
    bidding_timeout_ms: int = 500
    fallback_html: str | None = None
    fallback_click_url: str | None = None


@router.get("/config/{ad_unit_id}", response_model=SdkAdUnitConfig)
async def get_ad_unit_config(
    ad_unit_id: uuid.UUID,
    publisher: str = Query(...),
    device_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    au = await db.get(AdUnit, ad_unit_id)
    if not au:
        return SdkAdUnitConfig(
            ad_unit_id=str(ad_unit_id),
            ad_format="banner",
            width=None,
            height=None,
            waterfall=[],
            bidding=[],
            fallback_html="<div>No ad</div>",
        )

    result = await db.execute(
        select(AdSource)
        .where(
            AdSource.ad_unit_id == ad_unit_id,
            AdSource.status == "active",
        )
        .order_by(AdSource.priority.asc())
    )
    sources = list(result.scalars().all())

    waterfall = []
    bidding = []
    for s in sources:
        net = await db.get(AdNetwork, s.ad_network_id)
        net_name = net.name if net else s.instance_name
        entry = WaterfallEntry(
            source_id=str(s.id),
            network_name=net_name,
            ecpm=s.ecpm,
            priority=s.priority,
        )
        if s.bidding_endpoint:
            bidding.append(
                BiddingEntry(
                    source_id=str(s.id),
                    network_name=net_name,
                    endpoint=s.bidding_endpoint,
                )
            )
        else:
            waterfall.append(entry)

    waterfall.sort(key=lambda x: x.ecpm, reverse=True)
    bidding_config = au.bidding_config if isinstance(au.bidding_config, dict) else {}

    return SdkAdUnitConfig(
        ad_unit_id=str(au.id),
        ad_format=au.ad_format,
        width=au.width,
        height=au.height,
        waterfall=waterfall,
        bidding=bidding,
        bidding_timeout_ms=bidding_config.get("timeout_ms", 500),
        fallback_html=(
            '<div style="background:#eee;padding:20px;text-align:center">Ad</div>'
        ),
        fallback_click_url=None,
    )
