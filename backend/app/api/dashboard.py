"""Publisher Dashboard API - aggregate KPIs from events."""

import uuid

from datetime import datetime, timedelta, timezone

from typing import Optional


from fastapi import Depends, Query

from pydantic import BaseModel

from sqlalchemy import func, select

from sqlalchemy.ext.asyncio import AsyncSession


from app.core.database import get_db

from app.core.response import APIRouter

from app.core.security import require_permission

from app.models import ClickEvent, ConversionEvent, ImpressionEvent

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class KPICard(BaseModel):

    label: str

    value: float

    unit: str

    change: float = 0.0


class PublisherSummary(BaseModel):

    impressions: int

    clicks: int

    conversions: int

    revenue: float

    ecpm: float

    ctr: float

    kpis: list[KPICard]


@router.get("/summary", response_model=PublisherSummary)
async def get_summary(
    publisher_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission("campaign:read")),
):

    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    async def _count(model, since):

        stmt = select(func.count(model.id)).where(model.created_at >= since)

        if publisher_id:

            stmt = stmt.where(model.publisher_id == uuid.UUID(publisher_id))

        return (await db.execute(stmt)).scalar() or 0

    async def _sum_revenue(since):

        stmt = select(func.coalesce(func.sum(ImpressionEvent.revenue), 0.0)).where(
            ImpressionEvent.created_at >= since
        )

        if publisher_id:

            stmt = stmt.where(ImpressionEvent.publisher_id == uuid.UUID(publisher_id))

        return float((await db.execute(stmt)).scalar() or 0.0)

    imps_today = await _count(ImpressionEvent, today)

    clicks_today = await _count(ClickEvent, today)

    convs_today = await _count(ConversionEvent, today)

    revenue_today = await _sum_revenue(today)

    ecpm = (revenue_today / imps_today * 1000.0) if imps_today > 0 else 0.0

    ctr = (clicks_today / imps_today * 100.0) if imps_today > 0 else 0.0

    return PublisherSummary(
        impressions=imps_today,
        clicks=clicks_today,
        conversions=convs_today,
        revenue=revenue_today,
        ecpm=ecpm,
        ctr=ctr,
        kpis=[
            KPICard(label="Revenue", value=revenue_today, unit="$", change=0.0),
            KPICard(label="eCPM", value=ecpm, unit="$", change=0.0),
            KPICard(label="CTR", value=ctr, unit="%", change=0.0),
            KPICard(label="Impressions", value=float(imps_today), unit="", change=0.0),
        ],
    )


@router.get("/trend")
async def get_trend(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_permission("campaign:read")),
):

    now = datetime.now(timezone.utc)

    start = now - timedelta(days=days)

    result = await db.execute(
        select(
            func.strftime("%Y-%m-%d", ImpressionEvent.created_at).label("day"),
            func.count(ImpressionEvent.id).label("impressions"),
            func.coalesce(func.sum(ImpressionEvent.revenue), 0.0).label("revenue"),
        )
        .where(ImpressionEvent.created_at >= start)
        .group_by(func.strftime("%Y-%m-%d", ImpressionEvent.created_at))
        .order_by("day")
    )

    return {
        "trend": [
            {"date": r.day, "impressions": r.impressions, "revenue": float(r.revenue)}
            for r in result.all()
        ]
    }
