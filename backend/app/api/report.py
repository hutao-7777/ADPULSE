"""Report export API."""

import csv
import io
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import get_current_active_user
from app.models import ClickEvent, ConversionEvent, ImpressionEvent, User

router = APIRouter(prefix="/api/report", tags=["report"])


async def _daily_agg(
    db: AsyncSession, days: int, publisher_id: Optional[uuid.UUID] = None
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = []

    imps_r = await db.execute(
        select(
            func.strftime("%Y-%m-%d", ImpressionEvent.created_at).label("day"),
            func.count(ImpressionEvent.id).label("impressions"),
            func.coalesce(func.sum(ImpressionEvent.revenue), 0.0).label("revenue"),
        )
        .where(ImpressionEvent.created_at >= since)
        .group_by(func.strftime("%Y-%m-%d", ImpressionEvent.created_at))
        .order_by("day")
    )
    imps_by_day = {
        r.day: {"impressions": r.impressions, "revenue": float(r.revenue)}
        for r in imps_r.all()
    }

    clks_r = await db.execute(
        select(
            func.strftime("%Y-%m-%d", ClickEvent.created_at).label("day"),
            func.count(ClickEvent.id).label("clicks"),
        )
        .where(ClickEvent.created_at >= since)
        .group_by(func.strftime("%Y-%m-%d", ClickEvent.created_at))
    )
    clks_by_day = {r.day: r.clicks for r in clks_r.all()}

    convs_r = await db.execute(
        select(
            func.strftime("%Y-%m-%d", ConversionEvent.created_at).label("day"),
            func.count(ConversionEvent.id).label("convs"),
            func.coalesce(func.sum(ConversionEvent.event_value), 0.0).label(
                "conv_value"
            ),
        )
        .where(ConversionEvent.created_at >= since)
        .group_by(func.strftime("%Y-%m-%d", ConversionEvent.created_at))
    )
    convs_by_day = {
        r.day: {"convs": r.convs, "value": float(r.conv_value)} for r in convs_r.all()
    }

    for i in range(days):
        day = (since + timedelta(days=i)).strftime("%Y-%m-%d")
        imp = imps_by_day.get(day, {"impressions": 0, "revenue": 0.0})
        clicks = clks_by_day.get(day, 0)
        conv = convs_by_day.get(day, {"convs": 0, "value": 0.0})
        ecpm = (
            (imp["revenue"] / imp["impressions"] * 1000)
            if imp["impressions"] > 0
            else 0.0
        )
        ctr = (clicks / imp["impressions"] * 100) if imp["impressions"] > 0 else 0.0
        rows.append(
            {
                "date": day,
                "impressions": imp["impressions"],
                "clicks": clicks,
                "conversions": conv["convs"],
                "revenue": round(imp["revenue"], 4),
                "conv_value": round(conv["value"], 4),
                "ecpm": round(ecpm, 4),
                "ctr_pct": round(ctr, 4),
            }
        )
    return rows


@router.get("/summary")
async def export_summary(
    days: int = Query(7, ge=1, le=90),
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    data = await _daily_agg(db, days)
    if format == "json":
        return {"days": days, "rows": data}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Date",
            "Impressions",
            "Clicks",
            "Conversions",
            "Revenue",
            "Conv Value",
            "eCPM",
            "CTR %",
        ]
    )
    for row in data:
        writer.writerow(
            [
                row["date"],
                row["impressions"],
                row["clicks"],
                row["conversions"],
                row["revenue"],
                row["conv_value"],
                row["ecpm"],
                row["ctr_pct"],
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=adpulse_report_{days}d.csv"
        },
    )
