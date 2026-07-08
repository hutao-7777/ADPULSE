"""Agent toolset for programmatic bidding optimization."""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.models import Auction, BidRecord, Campaign, Creative, DailyMetric


async def _get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def _as_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def get_campaign_performance(campaign_id: str) -> Dict[str, Any]:
    """Return aggregated campaign performance for the last 7 days."""
    async with AsyncSessionLocal() as session:
        campaign_uuid = _as_uuid(campaign_id)
        campaign = None
        if campaign_uuid:
            campaign = await session.get(Campaign, campaign_uuid)

        since = datetime.now(timezone.utc) - timedelta(days=7)
        result = await session.execute(
            select(
                func.coalesce(func.sum(DailyMetric.impressions), 0).label(
                    "impressions"
                ),
                func.coalesce(func.sum(DailyMetric.clicks), 0).label("clicks"),
                func.coalesce(func.sum(DailyMetric.spend), 0.0).label("spend"),
                func.coalesce(func.sum(DailyMetric.revenue), 0.0).label("revenue"),
                func.coalesce(func.avg(DailyMetric.ctr), 0.0).label("avg_ctr"),
                func.coalesce(func.avg(DailyMetric.roi), 0.0).label("avg_roi"),
            )
            .where(DailyMetric.campaign_id == campaign_uuid)
            .where(DailyMetric.date >= since)
        )
        row = result.one()

        impressions = int(row.impressions or 0)
        clicks = int(row.clicks or 0)
        spend = float(row.spend or 0.0)
        revenue = float(row.revenue or 0.0)
        ctr = float(row.avg_ctr or 0.0)
        roi = float(row.avg_roi or 0.0)

        budget = campaign.budget if campaign else 0.0
        spend_ratio = spend / budget if budget > 0 else 0.0

        return {
            "campaign_id": campaign_id,
            "campaign_exists": campaign is not None,
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round(ctr, 6),
            "spend": round(spend, 4),
            "revenue": round(revenue, 4),
            "roi": round(roi, 4),
            "budget": round(budget, 4),
            "spend_ratio": round(spend_ratio, 4),
            "days": 7,
        }


async def get_auction_history(
    campaign_id: str, hours: int = 24
) -> List[Dict[str, Any]]:
    """Return recent auction records for a campaign."""
    async with AsyncSessionLocal() as session:
        campaign_uuid = _as_uuid(campaign_id)
        if not campaign_uuid:
            return []

        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await session.execute(
            select(Auction)
            .where(Auction.campaign_id == campaign_uuid)
            .where(Auction.created_at >= since)
            .order_by(Auction.created_at.desc())
        )
        auctions = result.scalars().all()

        records = []
        for auction in auctions:
            bids_result = await session.execute(
                select(BidRecord).where(BidRecord.auction_id == auction.id)
            )
            bids = bids_result.scalars().all()

            competitor_bids = [
                b.bid_amount * 1000.0 for b in bids if b.dsp_name != auction.winning_dsp
            ]
            records.append(
                {
                    "auction_id": auction.impression_id,
                    "auction_type": auction.auction_type,
                    "floor_price_cpm": round(auction.floor_price * 1000.0, 4),
                    "winning_bid_cpm": (
                        round(auction.winning_bid * 1000.0, 4)
                        if auction.winning_bid
                        else None
                    ),
                    "winning_dsp": auction.winning_dsp,
                    "total_bids": len(bids),
                    "avg_competitor_bid_cpm": (
                        round(sum(competitor_bids) / len(competitor_bids), 4)
                        if competitor_bids
                        else None
                    ),
                    "latency_ms": auction.latency_ms,
                    "created_at": (
                        auction.created_at.isoformat() if auction.created_at else None
                    ),
                }
            )
        return records


async def get_market_benchmark(
    geo: str, ad_format: str, category: str
) -> Dict[str, Any]:
    """Return mock market benchmark data for a segment."""
    # Deterministic pseudo-random based on input so the same segment is stable
    seed = hash((geo.lower(), ad_format.lower(), category.lower())) % 10000
    rng = random.Random(seed)

    base_cpm = {"tier1": 12.0, "tier2": 7.5, "tier3": 4.0}.get(geo, 8.0)
    base_ctr = {"banner_300x250": 0.025, "native": 0.035, "video_15s": 0.045}.get(
        ad_format, 0.025
    )

    avg_cpm = round(base_cpm * (0.9 + rng.random() * 0.2), 2)
    avg_ctr = round(base_ctr * (0.9 + rng.random() * 0.2), 6)
    competition_score = rng.random()
    competition_level = (
        "high"
        if competition_score > 0.66
        else "medium" if competition_score > 0.33 else "low"
    )

    return {
        "geo": geo,
        "ad_format": ad_format,
        "category": category,
        "avg_cpm": avg_cpm,
        "avg_ctr": avg_ctr,
        "competition_level": competition_level,
    }


async def adjust_bid(campaign_id: str, bid_adjustment_pct: float) -> Dict[str, Any]:
    """Simulate a bid adjustment and estimate its impact."""
    async with AsyncSessionLocal() as session:
        campaign_uuid = _as_uuid(campaign_id)
        campaign = None
        if campaign_uuid:
            campaign = await session.get(Campaign, campaign_uuid)

        current_cpm = 8.0
        if campaign and campaign.spent > 0 and campaign.budget > 0:
            # Use a heuristic current CPM derived from average auction if available
            auction_result = await session.execute(
                select(func.avg(Auction.winning_bid))
                .where(Auction.campaign_id == campaign_uuid)
                .where(Auction.winning_bid.isnot(None))
            )
            avg_bid = auction_result.scalar()
            if avg_bid:
                current_cpm = avg_bid * 1000.0

        new_cpm = current_cpm * (1 + bid_adjustment_pct)

        # Simple elasticity model
        impressions_change_pct = round(bid_adjustment_pct * 1.5 * 100.0, 2)
        # CTR changes slightly with bid because higher bids may win worse placements
        ctr_change_pct = round(bid_adjustment_pct * -0.1 * 100.0, 2)

        return {
            "campaign_id": campaign_id,
            "current_cpm": round(current_cpm, 4),
            "bid_adjustment_pct": round(bid_adjustment_pct, 4),
            "new_cpm": round(new_cpm, 4),
            "expected_impressions_change_pct": impressions_change_pct,
            "expected_ctr_change_pct": ctr_change_pct,
            "simulated": True,
        }


async def get_creative_performance(creative_id: str) -> Dict[str, Any]:
    """Return creative-level performance and fatigue data."""
    async with AsyncSessionLocal() as session:
        creative_uuid = _as_uuid(creative_id)
        creative = None
        if creative_uuid:
            creative = await session.get(Creative, creative_uuid)

        if creative is None:
            return {
                "creative_id": creative_id,
                "exists": False,
                "ai_score": 0.0,
                "fatigue_score": 0.0,
                "impressions": 0,
                "clicks": 0,
                "ctr": 0.0,
            }

        # Creative is not directly tied to DailyMetric in current schema,
        # so we return stored scores plus deterministic mock usage stats.
        seed = hash(str(creative.id)) % 10000
        rng = random.Random(seed)
        impressions = int(rng.randint(1000, 50000))
        ctr = round(rng.uniform(0.005, 0.06), 6)
        clicks = int(impressions * ctr)

        return {
            "creative_id": creative_id,
            "exists": True,
            "name": creative.name,
            "ai_score": creative.ai_score,
            "predicted_ctr": creative.predicted_ctr,
            "fatigue_score": creative.fatigue_score,
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
        }
