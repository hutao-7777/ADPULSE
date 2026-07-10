"""Dashboard aggregation API."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import APIRouter
from app.core.security import require_permission
from app.models import BidRecord, ClickRecord, ConvRecord, Creative, Experiment, Variant
from app.schemas.dashboard import KPISummary, RTBSummary, TrendPoint, WinRateTrend

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _source_filter(stmt, model, data_source: Optional[str]):
    """Apply optional data_source filter to a query."""
    if data_source and data_source != "all":
        return stmt.where(model.data_source == data_source)
    return stmt


class AvailableSourcesResponse(BaseModel):
    sources: list[dict]


@router.get("/available-sources")
async def get_available_sources(
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
):
    """Return list of available data sources and their bid record counts."""
    result = await db.execute(
        select(BidRecord.data_source, func.count(BidRecord.id)).group_by(
            BidRecord.data_source
        )
    )
    sources = []
    for row in result.all():
        name = row[0]
        label = {
            "mock": "Mock 数据",
            "ipinyou": "iPinYou 真实数据",
            "rtb_sim": "RTB 模拟数据",
        }.get(name, name)
        sources.append({"name": name, "label": label, "record_count": row[1]})
    return {"sources": sources}


@router.get("/creative-score-dist")
async def get_creative_score_distribution(
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> dict:
    """Return distribution of creative AI scores from the Creative table."""
    result = await db.execute(select(Creative.ai_score))
    scores = [row[0] for row in result.all() if row[0] is not None]

    buckets = ["0-20", "20-40", "40-60", "60-80", "80-100"]
    counts = [0, 0, 0, 0, 0]
    for score in scores:
        idx = min(int(score // 20), 4)
        counts[idx] += 1

    distribution = [{"range": b, "count": c} for b, c in zip(buckets, counts)]
    return {
        "distribution": distribution,
        "total": len(scores),
        "avg_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "data_source": data_source or "all",
    }


@router.get("/abtest-overview")
async def get_abtest_overview(
    limit: int = Query(5, ge=1, le=20),
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> dict:
    """Return latest running/completed A/B experiments with leading variant info."""
    from app.services.ab_test_engine import ABTestEngine

    engine = ABTestEngine()
    result = await db.execute(
        select(Experiment).order_by(Experiment.created_at.desc()).limit(limit)
    )
    experiments = result.scalars().all()

    items = []
    for exp in experiments:
        analysis = await engine.analyze(db, exp.id)
        variants = analysis.get("comparisons", [])
        control = analysis.get("control")

        if control is None:
            # Experiment has no metric data yet; skip from overview.
            continue

        leading_variant = control.get("name", "-")
        confidence = 0.0
        best_lift = 0.0
        for v in variants:
            if v.get("relative_lift_pct", 0) > best_lift:
                best_lift = v["relative_lift_pct"]
                leading_variant = v.get("variant_name", leading_variant)
                confidence = (1.0 - min(v.get("p_value_ttest", 1.0), 1.0)) * 100.0

        variant_count = (
            await db.execute(
                select(func.count(Variant.id)).where(Variant.experiment_id == exp.id)
            )
        ).scalar() or 0

        items.append(
            {
                "id": str(exp.id),
                "name": exp.name,
                "status": exp.status,
                "variant_count": variant_count,
                "leading_variant": leading_variant,
                "confidence": round(min(confidence, 99.0), 1),
                "metric": exp.metric_name,
            }
        )

    return {"experiments": items, "data_source": data_source or "all"}


@router.get("/summary")
async def get_dashboard_summary(
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> dict:
    """High-level campaign metrics."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    imp_stmt = select(func.count(BidRecord.id)).where(
        BidRecord.is_win.is_(True), BidRecord.timestamp >= today_start
    )
    imp_stmt = _source_filter(imp_stmt, BidRecord, data_source)
    total_imps = (await db.execute(imp_stmt)).scalar() or 0

    click_stmt = select(func.count(ClickRecord.id)).where(
        ClickRecord.timestamp >= today_start
    )
    click_stmt = _source_filter(click_stmt, ClickRecord, data_source)
    total_clicks = (await db.execute(click_stmt)).scalar() or 0

    conv_stmt = select(func.count(ConvRecord.id)).where(
        ConvRecord.timestamp >= today_start
    )
    conv_stmt = _source_filter(conv_stmt, ConvRecord, data_source)
    total_convs = (await db.execute(conv_stmt)).scalar() or 0

    spend_stmt = select(func.sum(BidRecord.pay_price)).where(
        BidRecord.is_win.is_(True), BidRecord.timestamp >= today_start
    )
    spend_stmt = _source_filter(spend_stmt, BidRecord, data_source)
    total_spend = (await db.execute(spend_stmt)).scalar() or 0.0

    return {
        "impressions": total_imps,
        "clicks": total_clicks,
        "conversions": total_convs,
        "spend": round(float(total_spend), 4),
        "revenue": 0.0,
        "data_source": data_source or "all",
    }


@router.get("/rtb-summary", response_model=RTBSummary)
async def get_rtb_summary(
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> RTBSummary:
    """Aggregate RTB metrics for today."""
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_stmt = select(func.count(BidRecord.id)).where(
        BidRecord.timestamp >= today_start
    )
    total_stmt = _source_filter(total_stmt, BidRecord, data_source)
    total_auctions = (await db.execute(total_stmt)).scalar() or 0

    wins_stmt = select(func.count(BidRecord.id)).where(
        BidRecord.is_win.is_(True), BidRecord.timestamp >= today_start
    )
    wins_stmt = _source_filter(wins_stmt, BidRecord, data_source)
    total_wins = (await db.execute(wins_stmt)).scalar() or 0

    avg_stmt = select(func.avg(BidRecord.pay_price)).where(
        BidRecord.is_win.is_(True), BidRecord.timestamp >= today_start
    )
    avg_stmt = _source_filter(avg_stmt, BidRecord, data_source)
    avg_winning_bid = (await db.execute(avg_stmt)).scalar() or 0.0

    fill_rate = total_wins / total_auctions if total_auctions > 0 else 0.0

    return RTBSummary(
        total_auctions_today=total_auctions,
        total_wins=total_wins,
        avg_winning_cpm=(avg_winning_bid or 0.0) * 1000.0,
        fill_rate=fill_rate,
        total_latency_avg_ms=0.0,
        data_source=data_source or "all",
    )


@router.get("/win-rate-trend", response_model=WinRateTrend)
async def get_win_rate_trend(
    period: str = Query("7d", pattern="^(7d|24h)$"),
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> WinRateTrend:
    """Return win-rate trend over the last 7 days or 24 hours."""
    now = datetime.now(timezone.utc)
    if period == "24h":
        start = now - timedelta(hours=24)
        group_expr = func.strftime("%Y-%m-%d %H:00", BidRecord.timestamp)
        labels = [
            (start + timedelta(hours=i)).strftime("%Y-%m-%d %H:00") for i in range(25)
        ]
    else:
        start = now - timedelta(days=7)
        group_expr = func.strftime("%Y-%m-%d", BidRecord.timestamp)
        labels = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(8)]

    auctions_subq = _source_filter(
        select(group_expr.label("bucket"), func.count(BidRecord.id).label("cnt"))
        .where(BidRecord.timestamp >= start)
        .group_by(group_expr),
        BidRecord,
        data_source,
    ).subquery()

    wins_subq = _source_filter(
        select(
            group_expr.label("bucket"),
            func.count(BidRecord.id).label("cnt"),
            func.avg(BidRecord.pay_price).label("avg_bid"),
        )
        .where(BidRecord.is_win.is_(True), BidRecord.timestamp >= start)
        .group_by(group_expr),
        BidRecord,
        data_source,
    ).subquery()

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
                data_source=data_source or "all",
            )
        )

    return WinRateTrend(period=period, data=data, data_source=data_source or "all")


@router.get("/kpi-summary", response_model=KPISummary)
async def get_kpi_summary(
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> KPISummary:
    """Return real KPI cards for the dashboard: eCPM, CTR, Fill Rate, ROI."""
    now = datetime.now(timezone.utc)

    def _today_start(offset_days: int = 0) -> datetime:
        return (now - timedelta(days=offset_days)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    async def _day_metrics(day_start: datetime) -> Dict[str, float]:
        next_day = day_start + timedelta(days=1)

        auctions_stmt = select(func.count(BidRecord.id)).where(
            BidRecord.timestamp >= day_start, BidRecord.timestamp < next_day
        )
        auctions_stmt = _source_filter(auctions_stmt, BidRecord, data_source)
        auctions = (await db.execute(auctions_stmt)).scalar() or 0

        wins_stmt = select(func.count(BidRecord.id)).where(
            BidRecord.is_win.is_(True),
            BidRecord.timestamp >= day_start,
            BidRecord.timestamp < next_day,
        )
        wins_stmt = _source_filter(wins_stmt, BidRecord, data_source)
        wins = (await db.execute(wins_stmt)).scalar() or 0

        spend_stmt = select(func.sum(BidRecord.pay_price)).where(
            BidRecord.is_win.is_(True),
            BidRecord.timestamp >= day_start,
            BidRecord.timestamp < next_day,
        )
        spend_stmt = _source_filter(spend_stmt, BidRecord, data_source)
        spend = float((await db.execute(spend_stmt)).scalar() or 0.0)

        clicks_stmt = select(func.count(ClickRecord.id)).where(
            ClickRecord.timestamp >= day_start, ClickRecord.timestamp < next_day
        )
        clicks_stmt = _source_filter(clicks_stmt, ClickRecord, data_source)
        clicks = (await db.execute(clicks_stmt)).scalar() or 0

        revenue_stmt = select(func.sum(ConvRecord.conv_value)).where(
            ConvRecord.timestamp >= day_start, ConvRecord.timestamp < next_day
        )
        revenue_stmt = _source_filter(revenue_stmt, ConvRecord, data_source)
        revenue = float((await db.execute(revenue_stmt)).scalar() or 0.0)

        impressions = wins
        ecpm = (spend / impressions * 1000.0) if impressions > 0 else 0.0
        ctr = clicks / impressions if impressions > 0 else 0.0
        fill_rate = wins / auctions if auctions > 0 else 0.0
        roi = revenue / spend if spend > 0 else 0.0

        return {
            "ecpm": ecpm,
            "ctr": ctr,
            "fill_rate": fill_rate,
            "roi": roi,
        }

    today_metrics = await _day_metrics(_today_start(0))
    yesterday_metrics = await _day_metrics(_today_start(1))

    trend: Dict[str, List[float]] = {"ecpm": [], "ctr": [], "fill_rate": [], "roi": []}
    for offset in range(6, -1, -1):
        day_metrics = await _day_metrics(_today_start(offset))
        trend["ecpm"].append(day_metrics["ecpm"])
        trend["ctr"].append(day_metrics["ctr"])
        trend["fill_rate"].append(day_metrics["fill_rate"])
        trend["roi"].append(day_metrics["roi"])

    def _change(current: float, previous: float) -> float:
        if previous == 0:
            return 0.0
        return ((current - previous) / previous) * 100.0

    kpis = [
        {
            "label": "eCPM",
            "value": today_metrics["ecpm"],
            "unit": "¥",
            "change": _change(today_metrics["ecpm"], yesterday_metrics["ecpm"]),
            "trend": trend["ecpm"],
        },
        {
            "label": "CTR",
            "value": today_metrics["ctr"] * 100.0,
            "unit": "%",
            "change": _change(today_metrics["ctr"], yesterday_metrics["ctr"]),
            "trend": [v * 100.0 for v in trend["ctr"]],
        },
        {
            "label": "Fill Rate",
            "value": today_metrics["fill_rate"] * 100.0,
            "unit": "%",
            "change": _change(
                today_metrics["fill_rate"], yesterday_metrics["fill_rate"]
            ),
            "trend": [v * 100.0 for v in trend["fill_rate"]],
        },
        {
            "label": "ROI",
            "value": today_metrics["roi"],
            "unit": "x",
            "change": _change(today_metrics["roi"], yesterday_metrics["roi"]),
            "trend": trend["roi"],
        },
    ]

    return KPISummary(
        kpis=kpis,  # type: ignore[arg-type]
        data_source=data_source or "all",
    )


@router.get("/campaign-budgets")
async def get_campaign_budgets(
    data_source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: Any = Depends(require_permission("campaign:read")),
) -> dict:
    """Return campaign budget consumption for the dashboard."""
    from app.models import Campaign

    result = await db.execute(
        select(Campaign.name, Campaign.budget, Campaign.spent)
        .where(Campaign.status.in_(["active", "paused"]))
        .order_by(Campaign.created_at.desc())
        .limit(5)
    )
    budgets = []
    for row in result.all():
        name, budget, spent = row
        pct = round((spent / budget * 100.0), 2) if budget and budget > 0 else 0.0
        budgets.append({"name": name, "spent_pct": min(pct, 100.0)})
    return {"budgets": budgets, "data_source": data_source or "all"}
