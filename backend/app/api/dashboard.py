"""Dashboard aggregation API."""

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.models.models import Auction
from app.schemas.dashboard import RTBSummary, TrendPoint, WinRateTrend

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_dashboard_summary() -> dict:
    """High-level campaign metrics placeholder."""
    return {
        "impressions": 0,
        "clicks": 0,
        "conversions": 0,
        "spend": 0.0,
        "revenue": 0.0,
    }


@router.get("/rtb-summary", response_model=RTBSummary)
async def get_rtb_summary(db: AsyncSession = Depends(get_db)) -> RTBSummary:
    """Aggregate RTB metrics for today."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_result = await db.execute(
        select(func.count(Auction.id)).where(Auction.created_at >= today_start)
    )
    total_auctions = total_result.scalar() or 0

    wins_result = await db.execute(
        select(func.count(Auction.id))
        .where(Auction.created_at >= today_start)
        .where(Auction.winning_dsp.isnot(None))
    )
    total_wins = wins_result.scalar() or 0

    avg_result = await db.execute(
        select(func.avg(Auction.winning_bid))
        .where(Auction.created_at >= today_start)
        .where(Auction.winning_bid.isnot(None))
    )
    avg_winning_bid = avg_result.scalar() or 0.0

    latency_result = await db.execute(
        select(func.avg(Auction.latency_ms)).where(Auction.created_at >= today_start)
    )
    avg_latency = latency_result.scalar() or 0.0

    fill_rate = total_wins / total_auctions if total_auctions > 0 else 0.0

    return RTBSummary(
        total_auctions_today=total_auctions,
        total_wins=total_wins,
        avg_winning_cpm=avg_winning_bid * 1000.0,
        fill_rate=fill_rate,
        total_latency_avg_ms=float(avg_latency),
    )


@router.get("/win-rate-trend", response_model=WinRateTrend)
async def get_win_rate_trend(
    period: str = Query("7d", pattern="^(7d|24h)$"),
    db: AsyncSession = Depends(get_db),
) -> WinRateTrend:
    """Return win-rate trend over the last 7 days or 24 hours."""
    now = datetime.now(timezone.utc)
    if period == "24h":
        start = now - timedelta(hours=24)
        group_expr = func.strftime("%Y-%m-%d %H:00", Auction.created_at)
        labels = [
            (start + timedelta(hours=i)).strftime("%Y-%m-%d %H:00") for i in range(25)
        ]
    else:
        start = now - timedelta(days=7)
        group_expr = func.strftime("%Y-%m-%d", Auction.created_at)
        labels = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(8)]

    auctions_subq = (
        select(group_expr.label("bucket"), func.count(Auction.id).label("cnt"))
        .where(Auction.created_at >= start)
        .group_by(group_expr)
        .subquery()
    )
    wins_subq = (
        select(
            group_expr.label("bucket"),
            func.count(Auction.id).label("cnt"),
            func.avg(Auction.winning_bid).label("avg_bid"),
        )
        .where(Auction.created_at >= start)
        .where(Auction.winning_dsp.isnot(None))
        .group_by(group_expr)
        .subquery()
    )

    result = await db.execute(
        select(
            auctions_subq.c.bucket,
            auctions_subq.c.cnt.label("auctions"),
            func.coalesce(wins_subq.c.cnt, 0).label("wins"),
            func.coalesce(wins_subq.c.avg_bid, 0.0).label("avg_bid"),
        ).outerjoin(wins_subq, auctions_subq.c.bucket == wins_subq.c.bucket)
    )

    rows = {row.bucket: row for row in result.all()}

    data: List[TrendPoint] = []
    for label in labels:
        row = rows.get(label)
        auctions = row.auctions if row else 0
        wins = row.wins if row else 0
        avg_bid = row.avg_bid if row else 0.0
        data.append(
            TrendPoint(
                label=label,
                auctions=auctions,
                wins=wins,
                win_rate=wins / auctions if auctions > 0 else 0.0,
                avg_cpm=(avg_bid or 0.0) * 1000.0,
            )
        )

    return WinRateTrend(period=period, data=data)
