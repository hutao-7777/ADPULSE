"""iPinYou RTB dataset API endpoints."""

from datetime import date
from typing import Any, List, Optional

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import require_permission
from app.models import (
    IpinyouBid,
    IpinyouClick,
    IpinyouConv,
    IpinyouDailyStat,
    IpinyouImp,
)
from app.schemas.ipinyou import (
    IpinyouAuctionListOut,
    IpinyouBidDetailOut,
    IpinyouBidOut,
    IpinyouClickOut,
    IpinyouConvOut,
    IpinyouDailyStatOut,
    IpinyouImpOut,
    IpinyouSummaryOut,
)

router = APIRouter(prefix="/api/v1/ipinyou", tags=["ipinyou"])


@router.get("/stats/daily", response_model=List[IpinyouDailyStatOut])
async def get_daily_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> List[IpinyouDailyStatOut]:
    """Return daily aggregated statistics, optionally filtered by date range."""
    stmt = select(IpinyouDailyStat).order_by(IpinyouDailyStat.date.asc())

    if start_date:
        stmt = stmt.where(IpinyouDailyStat.date >= start_date)
    if end_date:
        stmt = stmt.where(IpinyouDailyStat.date <= end_date)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [IpinyouDailyStatOut.model_validate(row) for row in rows]


@router.get("/stats/summary", response_model=IpinyouSummaryOut)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> IpinyouSummaryOut:
    """Return high-level summary across all imported iPinYou records."""
    total_bids_result = await db.execute(select(func.count(IpinyouBid.id)))
    total_bids = total_bids_result.scalar() or 0

    impressions_result = await db.execute(
        select(func.count(IpinyouBid.id)).where(IpinyouBid.is_win.is_(True))
    )
    total_impressions = impressions_result.scalar() or 0

    clicks_result = await db.execute(
        select(func.count(IpinyouBid.id)).where(IpinyouBid.is_clicked.is_(True))
    )
    total_clicks = clicks_result.scalar() or 0

    conversions_result = await db.execute(
        select(func.count(IpinyouBid.id)).where(IpinyouBid.is_converted.is_(True))
    )
    total_conversions = conversions_result.scalar() or 0

    cost_result = await db.execute(
        select(func.sum(IpinyouBid.paying_price)).where(IpinyouBid.is_win.is_(True))
    )
    total_cost = cost_result.scalar() or 0.0

    avg_ctr = total_clicks / total_impressions if total_impressions else 0.0
    avg_cpm = (total_cost / total_impressions) * 1000 if total_impressions else 0.0

    return IpinyouSummaryOut(
        total_bids=total_bids,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        total_conversions=total_conversions,
        total_cost=round(total_cost, 4),
        avg_ctr=round(avg_ctr, 6),
        avg_cpm=round(avg_cpm, 4),
    )


@router.get("/auctions", response_model=IpinyouAuctionListOut)
async def list_auctions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> IpinyouAuctionListOut:
    """Return a paginated list of bid/auction records."""
    total_result = await db.execute(select(func.count(IpinyouBid.id)))
    total = total_result.scalar() or 0

    stmt = (
        select(IpinyouBid)
        .order_by(desc(IpinyouBid.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return IpinyouAuctionListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[IpinyouBidOut.model_validate(item) for item in items],
    )


@router.get("/auctions/{bid_id}", response_model=IpinyouBidDetailOut)
async def get_auction_detail(
    bid_id: str,
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> IpinyouBidDetailOut:
    """Return a single auction with its related impression, click and conversion."""
    bid_result = await db.execute(select(IpinyouBid).where(IpinyouBid.bid_id == bid_id))
    bid = bid_result.scalar_one_or_none()
    if bid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found"
        )

    imp_result = await db.execute(select(IpinyouImp).where(IpinyouImp.bid_id == bid_id))
    click_result = await db.execute(
        select(IpinyouClick).where(IpinyouClick.bid_id == bid_id)
    )
    conv_result = await db.execute(
        select(IpinyouConv).where(IpinyouConv.bid_id == bid_id)
    )

    detail = IpinyouBidDetailOut.model_validate(bid)
    imp = imp_result.scalar_one_or_none()
    click = click_result.scalar_one_or_none()
    conv = conv_result.scalar_one_or_none()
    detail.impression = IpinyouImpOut.model_validate(imp) if imp else None
    detail.click = IpinyouClickOut.model_validate(click) if click else None
    detail.conversion = IpinyouConvOut.model_validate(conv) if conv else None
    return detail
