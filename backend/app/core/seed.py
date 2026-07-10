"""Seed mock data for local development and integration tests."""

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import cast

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    ApiKey,
    BidRecord,
    Campaign,
    ClickRecord,
    ConvRecord,
    Creative,
    DailyMetric,
    DailyStat,
    Experiment,
    ExperimentMetric,
    ImpRecord,
    Permission,
    Role,
    User,
    Variant,
    role_permissions,
    user_roles,
)

NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _uuid(name: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, name)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def seed_data(session: AsyncSession | None = None, reset: bool = False) -> None:
    """Seed deterministic mock data using INSERT OR IGNORE semantics.

    When ``reset`` is True, existing rows are deleted first so that development
    environments can start from a clean slate.
    """
    if session is None:
        async with AsyncSessionLocal() as session:
            await _seed_all(session, reset=reset)
    else:
        await _seed_all(session, reset=reset)


async def _seed_all(session: AsyncSession, reset: bool = False) -> None:
    if reset:
        await _reset_tables(session)
    await _seed_auth(session)
    await _seed_campaigns(session)
    await _seed_daily_metrics(session)
    await _seed_creatives(session)
    await _seed_unified_records(session)
    await _seed_ab_tests(session)
    await _seed_traffic_quality(session)


async def _reset_tables(session: AsyncSession) -> None:
    """Delete all rows from application tables in a safe order."""
    from sqlalchemy import text

    tables = [
        "experiment_daily_stats",
        "experiment_metrics",
        "assignments",
        "variants",
        "experiments",
        "fraud_alerts",
        "traffic_quality_scores",
        "daily_metrics",
        "creatives",
        "campaigns",
        "daily_stats",
        "bid_records",
        "imp_records",
        "click_records",
        "conv_records",
        "api_keys",
        "refresh_tokens",
        "user_roles",
        "role_permissions",
        "users",
        "roles",
        "permissions",
    ]
    for table in tables:
        try:
            await session.execute(text(f"DELETE FROM {table}"))
        except Exception:
            pass
    await session.commit()


async def _seed_auth(session: AsyncSession) -> None:
    """Seed default roles, permissions and a demo admin user."""
    permission_codes = [
        "user:write",
        "campaign:read",
        "campaign:write",
        "apikey:write",
        "rtb:write",
    ]
    permissions = [
        {"id": _uuid(f"permission-{code}"), "code": code} for code in permission_codes
    ]
    await session.execute(
        sqlite_insert(Permission)
        .values(permissions)
        .on_conflict_do_nothing(index_elements=["id"])
    )

    role_defs = {
        "admin": permission_codes,
        "advertiser": ["campaign:read", "campaign:write", "apikey:write"],
        "viewer": ["campaign:read"],
    }
    role_records = {}
    for role_name, perms in role_defs.items():
        role_id = _uuid(f"role-{role_name}")
        role_records[role_name] = role_id
        await session.execute(
            sqlite_insert(Role)
            .values({"id": role_id, "name": role_name})
            .on_conflict_do_nothing(index_elements=["id"])
        )
        role_perms = []
        for code in perms:
            perm_id = _uuid(f"permission-{code}")
            role_perms.append({"role_id": role_id, "permission_id": perm_id})
        if role_perms:
            await session.execute(
                sqlite_insert(role_permissions)
                .values(role_perms)
                .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
            )

    admin_id = _uuid("user-admin")
    await session.execute(
        sqlite_insert(User)
        .values(
            {
                "id": admin_id,
                "email": "admin@example.com",
                "hashed_password": get_password_hash("admin123"),
                "full_name": "Demo Admin",
                "is_active": True,
                "is_superuser": True,
            }
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.execute(
        sqlite_insert(user_roles)
        .values({"user_id": admin_id, "role_id": role_records["admin"]})
        .on_conflict_do_nothing(index_elements=["user_id", "role_id"])
    )

    api_key_id = _uuid("apikey-demo-dsp")
    await session.execute(
        sqlite_insert(ApiKey)
        .values(
            {
                "id": api_key_id,
                "user_id": admin_id,
                "name": "Demo DSP Key",
                "key_prefix": "adpulse_",
                "key_hash": get_password_hash("adpulse_demo_dsp_key"),
                "scopes": ["rtb:write"],
                "rate_limit_rps": 1000,
                "is_active": True,
            }
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )

    await session.commit()


SEED_CAMPAIGNS = {
    "Summer Sale 2026": _uuid("campaign-summer-sale-2026"),
    "App Install Q3": _uuid("campaign-app-install-q3"),
    "Brand Awareness": _uuid("campaign-brand-awareness"),
}


async def _seed_campaigns(session: AsyncSession) -> None:
    campaigns = [
        {
            "id": _uuid("campaign-summer-sale-2026"),
            "name": "Summer Sale 2026",
            "status": "active",
            "budget": 10000.0,
            "spent": 3450.0,
            "start_date": _now() - timedelta(days=7),
            "target_cpa": 45.0,
            "created_at": _now() - timedelta(days=7),
        },
        {
            "id": _uuid("campaign-app-install-q3"),
            "name": "App Install Q3",
            "status": "active",
            "budget": 5000.0,
            "spent": 1200.0,
            "start_date": _now() - timedelta(days=5),
            "target_cpa": 30.0,
            "created_at": _now() - timedelta(days=5),
        },
        {
            "id": _uuid("campaign-brand-awareness"),
            "name": "Brand Awareness",
            "status": "paused",
            "budget": 20000.0,
            "spent": 8900.0,
            "start_date": _now() - timedelta(days=14),
            "target_cpa": 60.0,
            "created_at": _now() - timedelta(days=14),
        },
    ]
    await session.execute(
        sqlite_insert(Campaign)
        .values(campaigns)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()


async def _seed_daily_metrics(session: AsyncSession) -> None:
    campaign_ids = [
        _uuid("campaign-summer-sale-2026"),
        _uuid("campaign-app-install-q3"),
        _uuid("campaign-brand-awareness"),
    ]

    rng = random.Random(42)
    metrics = []
    for campaign_id in campaign_ids:
        for day_offset in range(7):
            date = (_now() - timedelta(days=6 - day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            impressions = rng.randint(1000, 5000)
            ctr = rng.uniform(0.01, 0.05)
            clicks = int(impressions * ctr)
            clicks = max(1, clicks)
            conversion_rate = rng.uniform(0.05, 0.15)
            conversions = int(clicks * conversion_rate)
            cpm = rng.uniform(2.0, 10.0)
            spend = impressions * cpm / 1000.0
            revenue_per_conversion = rng.uniform(20.0, 100.0)
            revenue = conversions * revenue_per_conversion

            metrics.append(
                {
                    "id": _uuid(f"daily-metric-{campaign_id}-{date.isoformat()}"),
                    "date": date,
                    "campaign_id": campaign_id,
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "spend": round(spend, 4),
                    "revenue": round(revenue, 4),
                    "ctr": round(clicks / impressions, 6),
                    "cpm": round(spend / impressions * 1000, 4),
                    "cpc": round(spend / clicks, 4),
                    "roi": round(revenue / spend, 4) if spend > 0 else 0.0,
                }
            )

    await session.execute(
        sqlite_insert(DailyMetric)
        .values(metrics)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()


async def _seed_creatives(session: AsyncSession) -> None:
    creatives = [
        {
            "id": _uuid("creative-summer-banner-v1"),
            "name": "summer_banner_v1",
            "campaign_id": _uuid("campaign-summer-sale-2026"),
            "image_path": "uploads/seed_summer_banner_v1.png",
            "file_type": "image/png",
            "is_active": True,
            "ai_score": 87.0,
            "predicted_ctr": 0.032,
            "fatigue_score": 0.25,
        },
        {
            "id": _uuid("creative-summer-banner-v2"),
            "name": "summer_banner_v2",
            "campaign_id": _uuid("campaign-summer-sale-2026"),
            "image_path": "uploads/seed_summer_banner_v2.png",
            "file_type": "image/png",
            "is_active": True,
            "ai_score": 72.0,
            "predicted_ctr": 0.025,
            "fatigue_score": 0.45,
        },
        {
            "id": _uuid("creative-app-install-native"),
            "name": "app_install_native",
            "campaign_id": _uuid("campaign-app-install-q3"),
            "image_path": "uploads/seed_app_install_native.png",
            "file_type": "image/png",
            "is_active": True,
            "ai_score": 91.0,
            "predicted_ctr": 0.041,
            "fatigue_score": 0.15,
        },
    ]
    await session.execute(
        sqlite_insert(Creative)
        .values(creatives)
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await session.commit()


async def _seed_ab_tests(session: AsyncSession) -> None:
    """Seed demo A/B experiments with realistic daily event data."""
    rng = random.Random(44)
    campaign_id = _uuid("campaign-summer-sale-2026")

    experiments = [
        {
            "id": _uuid("abtest-landing-cta"),
            "campaign_id": campaign_id,
            "name": "落地页按钮文案测试",
            "description": "测试 CTA 按钮文案对转化率的影响",
            "status": "running",
            "metric_name": "conversion_rate",
            "traffic_allocation": 80,
            "min_sample_size": 500,
            "max_duration_days": 14,
            "start_date": _now() - timedelta(days=7),
        },
        {
            "id": _uuid("abtest-headline"),
            "campaign_id": campaign_id,
            "name": "头图素材对比",
            "description": "对比不同头图素材的 CTR",
            "status": "running",
            "metric_name": "ctr",
            "traffic_allocation": 60,
            "min_sample_size": 800,
            "max_duration_days": 10,
            "start_date": _now() - timedelta(days=5),
        },
    ]
    await session.execute(
        sqlite_insert(Experiment).values(experiments).on_conflict_do_nothing()
    )

    variants = []
    for exp in experiments:
        variants.extend(
            [
                {
                    "id": _uuid(f"variant-{exp['id']}-control"),
                    "experiment_id": exp["id"],
                    "name": "control",
                    "traffic_pct": 0.5,
                    "config": {"color": "blue", "text": "立即购买"},
                },
                {
                    "id": _uuid(f"variant-{exp['id']}-treatment"),
                    "experiment_id": exp["id"],
                    "name": "treatment",
                    "traffic_pct": 0.5,
                    "config": {"color": "green", "text": "免费试用"},
                },
            ]
        )
    await session.execute(
        sqlite_insert(Variant).values(variants).on_conflict_do_nothing()
    )
    await session.commit()

    # Generate daily events for each experiment/variant.
    metrics = []
    for exp in experiments:
        control_id = _uuid(f"variant-{exp['id']}-control")
        treatment_id = _uuid(f"variant-{exp['id']}-treatment")
        exp_id = exp["id"]
        start = cast(datetime, exp["start_date"]) or (_now() - timedelta(days=7))
        days = 14
        base_ctr = 0.025 if exp["metric_name"] == "ctr" else 0.030
        base_cvr = 0.08 if exp["metric_name"] == "conversion_rate" else 0.06

        for day_offset in range(days):
            day_start = (start + timedelta(days=day_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            if day_start > _now():
                continue
            daily_users = rng.randint(80, 150)
            for variant_id, lift in [(control_id, 0.0), (treatment_id, 0.18)]:
                for u in range(daily_users):
                    user_id = f"user-{rng.randint(1, 100000)}"
                    ts = day_start + timedelta(minutes=rng.randint(0, 1439))
                    metrics.append(
                        {
                            "id": uuid.uuid4(),
                            "experiment_id": exp_id,
                            "variant_id": variant_id,
                            "user_id": user_id,
                            "metric_name": "exposure",
                            "metric_value": 1.0,
                            "event_time": ts,
                        }
                    )
                    ctr = base_ctr * (1 + lift)
                    if rng.random() < ctr:
                        metrics.append(
                            {
                                "id": uuid.uuid4(),
                                "experiment_id": exp_id,
                                "variant_id": variant_id,
                                "user_id": user_id,
                                "metric_name": "click",
                                "metric_value": 1.0,
                                "event_time": ts
                                + timedelta(seconds=rng.randint(5, 60)),
                            }
                        )
                        cvr = base_cvr * (1 + lift * 0.7)
                        if rng.random() < cvr:
                            metrics.append(
                                {
                                    "id": uuid.uuid4(),
                                    "experiment_id": exp_id,
                                    "variant_id": variant_id,
                                    "user_id": user_id,
                                    "metric_name": "conversion",
                                    "metric_value": round(rng.uniform(30.0, 150.0), 2),
                                    "event_time": ts
                                    + timedelta(seconds=rng.randint(61, 600)),
                                }
                            )

    def _chunks(rows: list[dict], size: int = 500):
        for i in range(0, len(rows), size):
            yield rows[i : i + size]

    for chunk in _chunks(metrics):
        await session.execute(
            sqlite_insert(ExperimentMetric).values(chunk).on_conflict_do_nothing()
        )
    await session.commit()

    # Generate aggregate daily stats for the seeded experiments.
    from app.services.experiment_simulator import experiment_simulator

    for exp in experiments:
        variant_result = await session.execute(
            select(Variant).where(Variant.experiment_id == cast(uuid.UUID, exp["id"]))
        )
        variants_list = list(variant_result.scalars().all())
        if not variants_list:
            continue
        start_date_value: date = cast(datetime, exp["start_date"]).date()
        await experiment_simulator.generate_history(
            cast(uuid.UUID, exp["id"]), variants_list, start_date_value, session
        )


async def _seed_traffic_quality(session: AsyncSession) -> None:
    """Seed demo traffic quality scores so fraud alerts come from real records."""
    from app.services.traffic_quality_engine import (
        TrafficQualityEngine,
        seed_traffic_metrics,
    )

    engine = TrafficQualityEngine()
    campaign_ids = [
        _uuid("campaign-summer-sale-2026"),
        _uuid("campaign-app-install-q3"),
    ]
    rng = random.Random(45)
    for campaign_id in campaign_ids:
        for metric in seed_traffic_metrics(campaign_id, days=7, rng=rng):
            await engine.save_assessment(
                session,
                uuid.UUID(metric["campaign_id"]),
                metric["date"],
                metric["raw_metrics"],
            )
        await engine.detect_anomalies(session, campaign_id, hours=24 * 7)


async def _seed_unified_records(session: AsyncSession) -> None:
    """Seed mock bid/impression/click/conversion records into unified tables."""
    from collections import defaultdict

    campaign_ids = [
        _uuid("campaign-summer-sale-2026"),
        _uuid("campaign-app-install-q3"),
        _uuid("campaign-brand-awareness"),
    ]

    rng = random.Random(43)
    bid_rows: list[dict] = []
    imp_rows: list[dict] = []
    click_rows: list[dict] = []
    conv_rows: list[dict] = []

    now = _now()
    for day_offset in range(7):
        day_start = (now - timedelta(days=6 - day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        for campaign_id in campaign_ids:
            advertiser = str(campaign_id)
            for i in range(200):
                bid_id = f"mock-bid-{campaign_id}-{day_offset}-{i}"
                bid_price = rng.uniform(1.0, 10.0)
                is_win = rng.random() < 0.35
                is_click = is_win and rng.random() < 0.05
                is_conv = is_click and rng.random() < 0.15
                ts = day_start + timedelta(minutes=rng.randint(0, 1439))
                bid_rows.append(
                    {
                        "data_source": "mock",
                        "bid_id": bid_id,
                        "timestamp": ts,
                        "advertiser_id": advertiser,
                        "user_id": f"user-{rng.randint(1, 5000)}",
                        "ad_slot": f"slot-{rng.randint(1, 10)}",
                        "bid_price": round(bid_price, 4),
                        "pay_price": (
                            round(bid_price * rng.uniform(0.7, 1.0), 4)
                            if is_win
                            else None
                        ),
                        "is_win": is_win,
                        "device_type": rng.choice(["mobile", "desktop", "tablet"]),
                        "os": rng.choice(["ios", "android", "windows", "macos"]),
                        "browser": rng.choice(["chrome", "safari", "firefox"]),
                        "url": f"https://example.com/page-{rng.randint(1, 100)}",
                    }
                )
                if is_win:
                    imp_rows.append(
                        {
                            "data_source": "mock",
                            "bid_id": bid_id,
                            "timestamp": ts + timedelta(seconds=rng.randint(1, 30)),
                            "advertiser_id": advertiser,
                            "user_id": f"user-{rng.randint(1, 5000)}",
                            "ad_slot": f"slot-{rng.randint(1, 10)}",
                            "pay_price": round(bid_price * rng.uniform(0.7, 1.0), 4),
                        }
                    )
                if is_click:
                    click_rows.append(
                        {
                            "data_source": "mock",
                            "click_id": bid_id,
                            "bid_id": bid_id,
                            "timestamp": ts + timedelta(seconds=rng.randint(31, 120)),
                            "user_id": f"user-{rng.randint(1, 5000)}",
                            "advertiser_id": advertiser,
                            "url": f"https://example.com/page-{rng.randint(1, 100)}",
                        }
                    )
                if is_conv:
                    conv_rows.append(
                        {
                            "data_source": "mock",
                            "conv_id": bid_id,
                            "click_id": bid_id,
                            "bid_id": bid_id,
                            "timestamp": ts + timedelta(seconds=rng.randint(121, 600)),
                            "user_id": f"user-{rng.randint(1, 5000)}",
                            "advertiser_id": advertiser,
                            "conv_type": "purchase",
                            "conv_value": round(rng.uniform(20.0, 200.0), 2),
                        }
                    )

    def _chunks(rows: list[dict], size: int = 500):
        for i in range(0, len(rows), size):
            yield rows[i : i + size]

    for chunk in _chunks(bid_rows):
        await session.execute(
            sqlite_insert(BidRecord).values(chunk).on_conflict_do_nothing()
        )
    for chunk in _chunks(imp_rows):
        await session.execute(
            sqlite_insert(ImpRecord).values(chunk).on_conflict_do_nothing()
        )
    for chunk in _chunks(click_rows):
        await session.execute(
            sqlite_insert(ClickRecord).values(chunk).on_conflict_do_nothing()
        )
    for chunk in _chunks(conv_rows):
        await session.execute(
            sqlite_insert(ConvRecord).values(chunk).on_conflict_do_nothing()
        )

    # Aggregate daily stats from the mock bid rows.
    daily: dict[tuple[str, date], dict] = defaultdict(
        lambda: {
            "total_bids": 0,
            "total_imps": 0,
            "total_clicks": 0,
            "total_convs": 0,
            "total_spend": 0.0,
            "bid_prices": [],
        }
    )
    win_bid_ids = {r["bid_id"] for r in imp_rows}
    click_bid_ids = {r["bid_id"] for r in click_rows}
    conv_bid_ids = {r["bid_id"] for r in conv_rows}
    for row in bid_rows:
        key = (row["data_source"], row["timestamp"].date())
        daily[key]["total_bids"] += 1
        daily[key]["bid_prices"].append(row["bid_price"])
        if row["bid_id"] in win_bid_ids:
            daily[key]["total_imps"] += 1
            if row.get("pay_price"):
                daily[key]["total_spend"] += row["pay_price"]
        if row["bid_id"] in click_bid_ids:
            daily[key]["total_clicks"] += 1
        if row["bid_id"] in conv_bid_ids:
            daily[key]["total_convs"] += 1

    daily_rows = []
    for (source, day), agg in daily.items():
        bids = agg["total_bids"]
        imps = agg["total_imps"]
        clicks = agg["total_clicks"]
        convs = agg["total_convs"]
        avg_bid_price = (
            sum(agg["bid_prices"]) / len(agg["bid_prices"])
            if agg["bid_prices"]
            else None
        )
        avg_ctr = clicks / imps if imps else None
        avg_cvr = convs / clicks if clicks else None
        daily_rows.append(
            {
                "data_source": source,
                "date": day,
                "total_bids": bids,
                "total_imps": imps,
                "total_clicks": clicks,
                "total_convs": convs,
                "total_spend": round(agg["total_spend"], 4),
                "avg_bid_price": round(avg_bid_price, 4) if avg_bid_price else None,
                "avg_ctr": round(avg_ctr, 6) if avg_ctr else None,
                "avg_cvr": round(avg_cvr, 6) if avg_cvr else None,
            }
        )

    await session.execute(
        sqlite_insert(DailyStat).values(daily_rows).on_conflict_do_nothing()
    )
    await session.commit()
